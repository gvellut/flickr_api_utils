from addict import Dict as Addict

from api_auth import auth_flickr

flickr = auth_flickr()
# resp = flickr.upload(
#     filename="/Users/guilhem/Downloads/52138336613_1c64c5df54_k.jpg",
#     title="Fleur",
#     tags="asdasd",
#     is_public=False,
#     format="etree",
#     timeout=15,
#     **{"async": 1},
# )

ticket_id = "436117-72157723976784366"  # resp.find("ticketid")
# comma-separated
resp = flickr.photos.upload.checkTickets(tickets=ticket_id)

resp = Addict(resp)
ticket_statuses = resp.uploader.ticket
photo_id = None
for status in ticket_statuses:
    if status.complete == 0:
        # not finished : do another pass for that ticket
        pass
    elif status.complete == 1:
        # OK
        photo_id = status.photoid
    elif status.complete == 2:
        # invalid
        pass

print(repr(resp))
