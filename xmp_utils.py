import xml.etree.ElementTree as ET

from PIL import Image

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XAP_NS = "http://ns.adobe.com/xap/1.0/"
DC_NS = "http://purl.org/dc/elements/1.1/"


class NoXMPPacketFound(Exception):
    pass


def extract_xmp(filepath):
    # Read in input file
    with Image.open(filepath) as im:
        # Loop through segments and search for XMP packet
        for segment, content in im.applist:
            marker, body = content.rsplit(b"\x00", 1)
            if segment == "APP1" and b"http://ns.adobe.com/xap/1.0/" in marker:
                return body

        raise NoXMPPacketFound("No XMP packet present in file")


def parse_xmp(xmp_bytes):
    xmp_root = ET.fromstring(xmp_bytes)
    return xmp_root


def get_label(xmp_root):
    desc = xmp_root.findall(f".//{{{RDF_NS}}}Description")
    desc = desc[0]
    label = desc.attrib.get("{" + XAP_NS + "}Label")
    return label


def get_tags(xmp_root):
    tags = xmp_root.findall(f".//{{{DC_NS}}}subject/{{{RDF_NS}}}Bag/{{{RDF_NS}}}li")
    tags = [tag.text for tag in tags]
    return tags


def get_title(xmp_root):
    title = xmp_root.findall(f".//{{{DC_NS}}}title/{{{RDF_NS}}}Alt/{{{RDF_NS}}}li")
    if title:
        title = title[0].text
        return title
    return None
