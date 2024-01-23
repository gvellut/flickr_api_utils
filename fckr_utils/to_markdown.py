import traceback

from addict import Dict as Addict
import click

from api_auth import auth_flickr

from . import hugo_lib as hug

POSTS_DIR = "/Users/guilhem/Documents/projects/github/website/hugo_project/content/post"
URL_FILEPATH = "/Users/guilhem/Documents/projects/github/website/flickr_gen/urls.txt"


class DuplicateFlickrPostError(Exception):
    pass


@click.command()
def to_markdown():
    posts = hug.parse_hugo_content(POSTS_DIR, only_toml=False)
    this_post = None
    for filepath, fm, _ in posts:
        if fm.get("flickr"):
            if this_post:
                raise DuplicateFlickrPostError("Multiple flickr posts")
            this_post = filepath
            # do not break so we can check if multiple Flickr posts

    if not this_post:
        raise click.ClickException("No post for flickr: Set 'flickr' to True in FM")

    urls = read_urls(URL_FILEPATH)
    print(f"{len(urls)} URLs found")
    photo_ids = extract_photo_ids(urls)
    photo_data = resolve_photos(photo_ids)
    markdowns = gen_markdown(photo_data)
    markdown = "\n\n".join(markdowns)
    append(this_post, markdown)


def read_urls(filepath):
    lines = []
    with open(filepath, "r") as file:
        for line in file:
            stripped_line = line.strip()
            if stripped_line:
                lines.append(stripped_line)

    return lines


def extract_photo_ids(urls):
    photo_ids = []
    for url in urls:
        try:
            photo_id = url.split("/")[5]
            if not photo_id:
                print(f"Invalid URL: {url}")
                continue

            photo_ids.append((url, photo_id))
        except Exception:
            print(f"Invalid URL: {url}")

    return photo_ids


def resolve_photos(photo_ids):
    flickr = auth_flickr()

    flickr_photos = []
    for url, photo_id in photo_ids:
        try:
            info = Addict(flickr.photos.getInfo(photo_id=photo_id))
            photo = info["photo"]

            # keep base url => may include album /in/...
            page_url = url
            medium_url = (
                f"https://live.staticflickr.com/{photo.server}/{photo_id}_"
                + f"{photo.secret}_z.jpg"
            )

            title = photo.title["_content"]

            flickr_photos.append((page_url, medium_url, title))
        except Exception as ex:
            print(f"Exception occurred with photo {photo_id}: {ex}")
            traceback.print_exc()

    return flickr_photos


def gen_markdown(photo_data):
    markdowns = []
    for page_url, medium_url, title in photo_data:
        title = title.replace('"', '\\"')
        markdown_link = f'[![]({medium_url} "{title}")]({page_url})'
        markdowns.append(markdown_link)

    return markdowns


def append(filepath, markdown):
    with open(filepath, "a") as file:
        file.write("\n\n")
        file.write(markdown)


if __name__ == "__main__":
    to_markdown()
