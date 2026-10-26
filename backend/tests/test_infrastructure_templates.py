"""Offline contracts for the standalone Learner Lab CloudFormation templates."""

import ast
import re
from collections.abc import Iterator
from ipaddress import ip_network
from pathlib import Path
from typing import Any

import pytest
import yaml

INFRASTRUCTURE = Path(__file__).resolve().parents[2] / "infrastructure"
ARCHITECTURES = ("a", "b", "c")
PSEUDO_PARAMETERS = {
    "AWS::AccountId",
    "AWS::NotificationARNs",
    "AWS::NoValue",
    "AWS::Partition",
    "AWS::Region",
    "AWS::StackId",
    "AWS::StackName",
    "AWS::URLSuffix",
}
Template = dict[str, Any]


def _load(architecture: str) -> Template:
    path = INFRASTRUCTURE / f"architecture-{architecture}" / "template.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _mappings(value: Any) -> Iterator[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _mappings(child)


def _resources(template: Template, resource_type: str) -> dict[str, dict]:
    return {
        name: resource
        for name, resource in template["Resources"].items()
        if resource["Type"] == resource_type
    }


def _compute(template: Template) -> tuple[str, dict]:
    instances = _resources(template, "AWS::EC2::Instance")
    if instances:
        [(name, resource)] = instances.items()
        return name, resource["Properties"]
    [launch_template] = _resources(template, "AWS::EC2::LaunchTemplate").values()
    [group_name] = _resources(template, "AWS::AutoScaling::AutoScalingGroup")
    return group_name, launch_template["Properties"]["LaunchTemplateData"]


def _script(template: Template) -> str:
    return _compute(template)[1]["UserData"]["Fn::Base64"]["Fn::Sub"]


def _tag_map(tags: list[dict]) -> dict:
    return {tag["Key"]: tag["Value"] for tag in tags}


@pytest.fixture(params=ARCHITECTURES)
def architecture(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def template(architecture: str) -> Template:
    return _load(architecture)


def test_backend_parameter_contract(template: Template) -> None:
    assert template["AWSTemplateFormatVersion"] == "2010-09-09"
    parameters = template["Parameters"]
    assert set(parameters) == {"InstanceType", "CaseId", "LatestAmiId"}
    assert parameters["InstanceType"]["Type"] == "String"
    assert parameters["InstanceType"]["Default"] == "t3.micro"
    assert set(parameters["InstanceType"]["AllowedValues"]) == {"t2.micro", "t3.micro"}
    assert parameters["CaseId"]["Type"] == "String"
    assert {key for key, value in parameters.items() if "Default" not in value} == {"CaseId"}
    ami = parameters["LatestAmiId"]
    assert ami["Type"] == "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"
    assert ami["Default"] == (
        "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
    )


def test_references_resolve_without_resource_dependency_cycles(template: Template) -> None:
    resources = template["Resources"]
    known = set(resources) | set(template["Parameters"]) | PSEUDO_PARAMETERS

    def references(value: Any) -> set[str]:
        found = set()
        for mapping in _mappings(value):
            if "Ref" in mapping:
                found.add(mapping["Ref"])
            if "Fn::GetAtt" in mapping:
                attribute = mapping["Fn::GetAtt"]
                found.add(attribute[0] if isinstance(attribute, list) else attribute.split(".")[0])
            if "Fn::Sub" in mapping:
                substitution = mapping["Fn::Sub"]
                assert isinstance(substitution, str)
                found.update(re.findall(r"\$\{([^!}][^}]*)\}", substitution))
        return {reference.split(".")[0] for reference in found}

    assert references(template) <= known
    graph = {}
    for name, resource in resources.items():
        dependencies = resource.get("DependsOn", [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        assert set(dependencies) <= resources.keys()
        graph[name] = (references(resource) & resources.keys()) | set(dependencies)

    def visit(name: str, ancestors: set[str]) -> None:
        assert name not in ancestors, f"Circular dependency: {ancestors} -> {name}"
        for dependency in graph[name]:
            visit(dependency, ancestors | {name})

    for name in graph:
        visit(name, set())


def test_public_subnets_have_distinct_azs_and_internet_routes(
    template: Template, architecture: str
) -> None:
    [(vpc_name, vpc)] = _resources(template, "AWS::EC2::VPC").items()
    assert vpc["Properties"]["EnableDnsSupport"] is True
    assert vpc["Properties"]["EnableDnsHostnames"] is True
    network = ip_network(vpc["Properties"]["CidrBlock"])
    subnets = _resources(template, "AWS::EC2::Subnet")
    expected_count = 1 if architecture == "a" else 2
    assert len(subnets) == expected_count
    cidrs = []
    az_indices = []
    for subnet in subnets.values():
        properties = subnet["Properties"]
        assert properties["VpcId"] == {"Ref": vpc_name}
        assert properties["MapPublicIpOnLaunch"] is True
        cidr = ip_network(properties["CidrBlock"])
        assert cidr.subnet_of(network) and cidr.prefixlen <= 27
        assert all(not cidr.overlaps(previous) for previous in cidrs)
        cidrs.append(cidr)
        index, zones = properties["AvailabilityZone"]["Fn::Select"]
        assert zones == {"Fn::GetAZs": ""}
        az_indices.append(index)
    assert sorted(az_indices) == list(range(expected_count))

    [(gateway_name, _)] = _resources(template, "AWS::EC2::InternetGateway").items()
    [(attachment_name, attachment)] = _resources(template, "AWS::EC2::VPCGatewayAttachment").items()
    assert attachment["Properties"] == {
        "VpcId": {"Ref": vpc_name},
        "InternetGatewayId": {"Ref": gateway_name},
    }
    [(route_name, route)] = _resources(template, "AWS::EC2::Route").items()
    assert route["DependsOn"] == attachment_name
    assert route["Properties"]["DestinationCidrBlock"] == "0.0.0.0/0"
    assert route["Properties"]["GatewayId"] == {"Ref": gateway_name}
    associations = _resources(template, "AWS::EC2::SubnetRouteTableAssociation")
    assert len(associations) == len(subnets)
    assert {a["Properties"]["SubnetId"]["Ref"] for a in associations.values()} == set(subnets)
    for association in associations.values():
        assert association["Properties"]["RouteTableId"] == route["Properties"]["RouteTableId"]
    compute_name, _ = _compute(template)
    dependencies = set(template["Resources"][compute_name]["DependsOn"])
    assert {route_name, *associations} <= dependencies


def test_no_iam_nat_or_administrative_access(template: Template) -> None:
    for resource in template["Resources"].values():
        assert not resource["Type"].startswith("AWS::IAM::")
        assert resource["Type"] not in {"AWS::EC2::NatGateway", "AWS::EC2::EIP"}
    for mapping in _mappings(template):
        assert not {"IamInstanceProfile", "KeyName", "ServiceLinkedRoleARN"} & mapping.keys()
        for rule in mapping.get("SecurityGroupIngress", []):
            assert (rule["IpProtocol"], rule["FromPort"], rule["ToPort"]) == ("tcp", 80, 80)
            assert "CidrIpv6" not in rule
    assert "${CaseId}" not in _script(template)


def test_compute_hardening_and_monitoring(template: Template, architecture: str) -> None:
    _, properties = _compute(template)
    assert properties["ImageId"] == {"Ref": "LatestAmiId"}
    assert properties["InstanceType"] == {"Ref": "InstanceType"}
    metadata = properties["MetadataOptions"]
    assert metadata["HttpTokens"] == "required"
    assert metadata["HttpEndpoint"] == "enabled"
    assert metadata["HttpPutResponseHopLimit"] == 1
    assert metadata["InstanceMetadataTags"] == "disabled"
    assert properties["Monitoring"] == (True if architecture == "a" else {"Enabled": True})
    [disk] = properties["BlockDeviceMappings"]
    assert disk["DeviceName"] == "/dev/xvda"
    assert disk["Ebs"] == {
        "VolumeSize": 8,
        "VolumeType": "gp3",
        "Encrypted": True,
        "DeleteOnTermination": True,
    }
    if architecture != "a":
        [interface] = properties["NetworkInterfaces"]
        assert interface["AssociatePublicIpAddress"] is True
        assert interface["DeleteOnTermination"] is True
        assert interface["DeviceIndex"] == 0
        assert "SubnetId" not in interface
        assert "Placement" not in properties


def test_topology_scaling_and_alb_security(template: Template, architecture: str) -> None:
    groups = _resources(template, "AWS::AutoScaling::AutoScalingGroup")
    load_balancers = _resources(template, "AWS::ElasticLoadBalancingV2::LoadBalancer")
    instances = _resources(template, "AWS::EC2::Instance")
    if architecture == "a":
        assert len(instances) == 1
        assert not groups and not load_balancers
        return
    assert not instances
    [(group_name, group)] = groups.items()
    properties = group["Properties"]
    minimum, maximum = (1, 3) if architecture == "b" else (2, 4)
    assert int(properties["MinSize"]) == int(properties["DesiredCapacity"]) == minimum
    assert int(properties["MaxSize"]) == maximum
    subnet_names = [subnet["Ref"] for subnet in properties["VPCZoneIdentifier"]]
    assert len(subnet_names) == (1 if architecture == "b" else 2)
    [balancer] = load_balancers.values()
    alb = balancer["Properties"]
    assert alb["Type"] == "application" and alb["Scheme"] == "internet-facing"
    assert {subnet["Ref"] for subnet in alb["Subnets"]} == set(
        _resources(template, "AWS::EC2::Subnet")
    )
    assert set(subnet_names) <= {subnet["Ref"] for subnet in alb["Subnets"]}
    [listener] = _resources(template, "AWS::ElasticLoadBalancingV2::Listener").values()
    assert listener["Properties"]["Protocol"] == "HTTP"
    assert listener["Properties"]["Port"] == 80
    target_name = listener["Properties"]["DefaultActions"][0]["TargetGroupArn"]["Ref"]
    assert properties["TargetGroupARNs"] == [{"Ref": target_name}]
    target = template["Resources"][target_name]["Properties"]
    assert target["TargetType"] == "instance"
    assert target["Protocol"] == "HTTP" and target["Port"] == 80
    assert target["HealthCheckPath"] == "/health"
    assert target["Matcher"]["HttpCode"] == "200"
    attributes = {item["Key"]: item["Value"] for item in target["TargetGroupAttributes"]}
    assert attributes["load_balancing.cross_zone.enabled"] == "true"
    assert properties["HealthCheckType"] == "ELB"
    assert properties["HealthCheckGracePeriod"] >= 540
    assert properties["DefaultInstanceWarmup"] == 120
    assert properties["MetricsCollection"][0]["Granularity"] == "1Minute"
    assert "GroupInServiceInstances" in properties["MetricsCollection"][0]["Metrics"]

    _, compute = _compute(template)
    [interface] = compute["NetworkInterfaces"]
    [app_group] = interface["Groups"]
    ingress = template["Resources"][app_group["Ref"]]["Properties"]["SecurityGroupIngress"]
    assert len(ingress) == 1
    assert ingress[0]["SourceSecurityGroupId"] in alb["SecurityGroups"]
    assert "CidrIp" not in ingress[0]
    alb_group = template["Resources"][alb["SecurityGroups"][0]["Ref"]]["Properties"]
    assert alb_group["SecurityGroupIngress"][0]["CidrIp"] == "0.0.0.0/0"
    [policy] = _resources(template, "AWS::AutoScaling::ScalingPolicy").values()
    assert policy["Properties"]["AutoScalingGroupName"] == {"Ref": group_name}
    assert policy["Properties"]["PolicyType"] == "TargetTrackingScaling"
    tracking = policy["Properties"]["TargetTrackingConfiguration"]
    assert tracking["PredefinedMetricSpecification"] == {
        "PredefinedMetricType": "ASGAverageCPUUtilization"
    }
    assert tracking["TargetValue"] == 50.0
    assert tracking["DisableScaleIn"] is False
    assert properties["LaunchTemplate"]["Version"] == {
        "Fn::GetAtt": ["AppLaunchTemplate", "LatestVersionNumber"]
    }


def test_signals_gate_bootstrap_and_preserve_failures(
    template: Template, architecture: str
) -> None:
    resource_name, _ = _compute(template)
    resource = template["Resources"][resource_name]
    count = 2 if architecture == "c" else 1
    assert resource["CreationPolicy"]["ResourceSignal"] == {"Count": count, "Timeout": "PT12M"}
    script = _script(template)
    assert script.startswith("#!/bin/bash\nset -Eeuo pipefail\n")
    assert "trap signal_result EXIT" in script
    assert "status=$?" in script and 'exit "$status"' in script
    assert 'cfn-signal --exit-code "$status"' in script
    assert f"--resource {resource_name}" in script
    assert "--stack '${AWS::StackName}'" in script
    assert "--region '${AWS::Region}'" in script
    assert "timeout 20s /opt/aws/bin/cfn-signal" in script
    assert "timeout --signal=TERM --kill-after=10s 540s bash -Eeuo pipefail" in script
    assert "dnf install -y" in script and "nginx python3 aws-cfn-bootstrap" in script
    assert script.index("trap signal_result EXIT") < script.index("dnf install")
    for option in ("--access-key", "--secret-key", "--role", "--credential-file"):
        assert option not in script
    assert "curl --fail --silent --show-error --max-time 5 http://127.0.0.1/health" in script
    assert "curl --fail --silent --show-error --max-time 5 http://127.0.0.1/\n" in script
    if architecture != "a":
        assert resource["CreationPolicy"]["AutoScalingCreationPolicy"] == {
            "MinSuccessfulInstancesPercent": 100
        }
        rolling = resource["UpdatePolicy"]["AutoScalingRollingUpdate"]
        assert rolling["WaitOnResourceSignals"] is True
        assert rolling["MinSuccessfulInstancesPercent"] == 100
        assert rolling["MinInstancesInService"] == count
        assert rolling["PauseTime"] == "PT12M"


def test_case_tags_reach_instances_and_volumes(template: Template, architecture: str) -> None:
    for resource in template["Resources"].values():
        tags = resource["Properties"].get("Tags")
        if tags is not None:
            assert _tag_map(tags)["CaseId"] == {"Ref": "CaseId"}
    resource_name, compute = _compute(template)
    instance_tags = template["Resources"][resource_name]["Properties"]["Tags"]
    for tags in [instance_tags, *(s["Tags"] for s in compute.get("TagSpecifications", []))]:
        mapping = _tag_map(tags)
        assert mapping["CaseId"] == {"Ref": "CaseId"}
        assert mapping["Project"] == "SECI-TI"
        assert mapping["Architecture"] == architecture.upper()
        assert mapping["StackName"] == {"Ref": "AWS::StackName"}
    if architecture == "a":
        assert compute["PropagateTagsToVolumeOnCreation"] is True
    else:
        assert all(tag["PropagateAtLaunch"] is True for tag in instance_tags)
        assert {s["ResourceType"] for s in compute["TagSpecifications"]} >= {"volume"}


def test_outputs_support_application_and_future_metrics(
    template: Template, architecture: str
) -> None:
    outputs = template["Outputs"]
    assert outputs["VpcId"]["Value"] == {"Ref": "Vpc"}
    if architecture == "a":
        assert set(outputs) == {"ApplicationUrl", "VpcId", "InstanceId"}
        assert outputs["ApplicationUrl"]["Value"] == {"Fn::Sub": "http://${AppInstance.PublicIp}"}
        assert outputs["InstanceId"]["Value"] == {"Ref": "AppInstance"}
    else:
        assert set(outputs) == {
            "ApplicationUrl",
            "VpcId",
            "LoadBalancerFullName",
            "AutoScalingGroupName",
        }
        assert outputs["ApplicationUrl"]["Value"] == {"Fn::Sub": "http://${LoadBalancer.DNSName}"}
        assert outputs["LoadBalancerFullName"]["Value"] == {
            "Fn::GetAtt": ["LoadBalancer", "LoadBalancerFullName"]
        }
        assert outputs["AutoScalingGroupName"]["Value"] == {"Ref": "AppAutoScalingGroup"}


def test_demo_workload_is_identical_and_python_parses() -> None:
    applications = []
    for architecture in ARCHITECTURES:
        script = _script(_load(architecture))
        application = script.split("<<'PYTHON'\n", 1)[1].split("\nPYTHON\n", 1)[0]
        ast.parse(application)
        assert 'ThreadingHTTPServer(("127.0.0.1", 8000)' in application
        assert 'if self.path == "/":' in application
        assert '"/health"' in application
        assert "pbkdf2_hmac" in application
        applications.append(application)
    assert applications[0] == applications[1] == applications[2]
