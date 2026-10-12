"""Parse a Compose YAML file while accepting Docker Compose extension tags."""

import sys
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


def construct_compose_extension(loader, _tag_suffix, node):
	if isinstance(node, ScalarNode):
		return loader.construct_scalar(node)
	if isinstance(node, SequenceNode):
		return loader.construct_sequence(node)
	if isinstance(node, MappingNode):
		return loader.construct_mapping(node)
	raise yaml.constructor.ConstructorError(None, None, "Unsupported Compose YAML node", node.start_mark)


yaml.SafeLoader.add_multi_constructor("!", construct_compose_extension)


def main():
	for raw_path in sys.argv[1:]:
		path = Path(raw_path)
		with path.open(encoding="utf-8") as source:
			yaml.load(source, Loader=yaml.SafeLoader)
		print(f"Validated Docker Compose YAML: {path}")


if __name__ == "__main__":
	main()
