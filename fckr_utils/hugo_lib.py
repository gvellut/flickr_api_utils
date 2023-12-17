import glob

import toml

SEPARATOR = "+++"

DEFAULT_POST_DIRECTORY = "hugo_project/content/post"


def parse_hugo_content(directory=DEFAULT_POST_DIRECTORY, only_toml=False):
    files = glob.glob(directory + "/**/*.md", recursive=True)
    parsed_tomls = []
    for file in files:
        with open(file, "r") as f:
            content = f.read()
            contents = content.split(SEPARATOR, 2)
            toml_content = contents[1]
            post_content = contents[2].strip()
            parsed_toml = toml.loads(toml_content)
            parsed_tomls.append((file, parsed_toml, post_content))
    if only_toml:
        return [x[1] for x in parsed_tomls]
    return sorted(parsed_tomls, key=lambda x: x[0])
