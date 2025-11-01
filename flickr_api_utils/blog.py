import traceback

from addict import Dict as Addict
from attr import define
import click

from .api_auth import auth_flickr
from .hugo_lib import parse_hugo_content

DEFAULT_URLS_FILE = (
    "/Users/guilhem/Documents/projects/website/blog-vellut.com/flickr_gen/urls.txt"
)

DEFAULT_POSTS_DIR = (
    "/Users/guilhem/Documents/projects/website/blog-vellut.com/"
    "hugo_project/content/post"
)


@click.group("blog")
def blog():
    pass


class DuplicateFlickrPostError(Exception):
    pass


@define
class FlickrPhoto:
    title: str
    page_url: str
    medium_url: str
    medium_dims: tuple[int, int]
    raw_data: dict


@blog.command("to-markdown")
@click.option(
    "--posts-dir",
    default=DEFAULT_POSTS_DIR,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Hugo posts directory (e.g., hugo_project/content/post)",
)
@click.option(
    "--urls-file",
    default=DEFAULT_URLS_FILE,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Text file containing Flickr photo URLs (one per line)",
)
def to_markdown(posts_dir, urls_file):
    """Generate markdown for Flickr photos in a Hugo blog post.

    Reads Flickr photo URLs from a text file and appends markdown image
    links to the Hugo post that has 'flickr = true' in its front matter.
    """
    posts = parse_hugo_content(posts_dir, only_toml=False)
    this_post = None
    for filepath, fm, _ in posts:
        if fm.get("flickr"):
            if this_post:
                raise DuplicateFlickrPostError("Multiple flickr posts")
            this_post = filepath
            # do not break so we can check if multiple Flickr posts

    if not this_post:
        raise click.ClickException("No post for flickr: Set 'flickr' to True in FM")

    urls = read_urls(urls_file)
    click.echo(f"{len(urls)} URLs found")
    photo_ids = extract_photo_ids(urls)
    photo_data = resolve_photos(photo_ids)
    markdowns = gen_markdown(photo_data)
    markdown = "\n\n".join(markdowns)
    append(this_post, markdown)
    click.echo(f"Appended markdown for {len(photo_data)} photos to {this_post}")


def read_urls(filepath):
    """Read URLs from a text file, one per line."""
    lines = []
    with open(filepath) as file:
        for line in file:
            stripped_line = line.strip()
            if stripped_line:
                lines.append(stripped_line)

    return lines


def extract_photo_ids(urls):
    """Extract photo IDs from Flickr URLs."""
    photo_ids = []
    for url in urls:
        try:
            photo_id = url.split("/")[5]
            if not photo_id:
                raise Exception(f"Invalid URL: {url}")
            photo_ids.append((url, photo_id))
        except Exception:
            click.echo(f"Invalid URL: {url}", err=True)

    return photo_ids


def resolve_photos(photo_ids) -> list[FlickrPhoto]:
    """Fetch photo information from Flickr API."""
    flickr = auth_flickr()

    flickr_photos = []
    for url, photo_id in photo_ids:
        try:
            # will return all the info including location and date_taken / date_added
            info = Addict(flickr.photos.getInfo(photo_id=photo_id))
            photo = info.photo
            sizes = Addict(flickr.photos.getSizes(photo_id=photo_id))
            sizes = sizes.sizes

            # keep base url => may include album /in/...
            page_url = url
            for size in sizes.size:
                if size.label == "Medium 640":
                    # assume always there
                    medium_url = size.source
                    medium_dims = (size.width, size.height)
                    break

            title = photo.title["_content"]

            flickr_photos.append(
                FlickrPhoto(title, page_url, medium_url, medium_dims, photo)
            )
        except Exception as ex:
            click.echo(f"Exception occurred with photo {photo_id}: {ex}", err=True)
            traceback.print_exc()

    return flickr_photos


def gen_markdown(photo_data):
    """Generate markdown links for photos."""
    markdowns = []
    for photo in photo_data:
        title = photo.title.replace('"', '\\"')
        hash_part = f"#w={photo.medium_dims[0]}&h={photo.medium_dims[1]}"
        markdown_link = (
            f'[![]({photo.medium_url}{hash_part} "{title}")]({photo.page_url})'
        )
        markdowns.append(markdown_link)

    return markdowns


def append(filepath, markdown):
    """Append markdown to a file."""
    with open(filepath, "a") as file:
        file.write("\n\n")
        file.write(markdown)
