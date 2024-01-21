from aiofiles import open as aiopen
from aiofiles.os import remove
from requests import post, get
from urllib.parse import quote
from base64 import b64encode, b64decode
from json import loads as jloads


async def get_direct_download_links(url: str, usr: str = 'None', pswd: str = 'None'):
    links_list, path = {}, ''
    page_token, pgNo, turn_page = '', 0, False
    
    def authenticate(user, password):
        return "Basic " + b64encode(f"{user}:{password}".encode()).decode('ascii')
    
    def gdindexScrape(link, auth, payload, npath):
        link = link.rstrip('/') + '/'
        cpost = post
        resp = cpost(link, data=payload, headers={"authorization": auth})
        if resp.status_code != 200:
            raise Exception("ERROR: Could not Access your Entered URL!, Check your Username / Password")
        try: 
            nresp = jloads(b64decode((resp.text)[::-1][24:-20]).decode('utf-8'))
        except: 
            raise Exception("ERROR: Something Went Wrong. Check Index Link / Username / Password Valid or Not")
        nonlocal page_token, turn_page
        if (new_page_token := nresp.get("nextPageToken", False)):
            turn_page = True
            page_token = new_page_token
        
        if list(nresp.get("data").keys())[0] == "error":
            raise Exception("Nothing Found in your provided URL")
        
        data = {}
        files = nresp["data"]["files"]
        for i, _ in enumerate(range(len(files))):
            files_name = files[i]["name"]
            dl_link = f"{link}{quote(files_name)}"
            if files[i]["mimeType"] == "application/vnd.google-apps.folder":
                data.update(gdindexScrape(dl_link, auth, {"page_token": page_token, "page_index": 0}, npath + f"/{files_name}"))
            else:
                data[dl_link] = npath
        return data

    auth = authenticate(usr, pswd)
    links_list.update(gdindexScrape(url, auth, {"page_token": page_token, "page_index": pgNo}, path))
    while turn_page == True:
        links_list.update(gdindexScrape(url, auth, {"page_token": page_token, "page_index": pgNo}, path))
        pgNo += 1

    return links_list


def filterLinks(links_list: list, bulk_start: int, bulk_end: int) -> list:
    if bulk_start != 0 and bulk_end != 0:
        links_list = links_list[bulk_start:bulk_end]
    elif bulk_start != 0:
        links_list = links_list[bulk_start:]
    elif bulk_end != 0:
        links_list = links_list[:bulk_end]
    return links_list


def getLinksFromMessage(text: str) -> list:
    links_list = text.split("\n")
    return [item.strip() for item in links_list if len(item) != 0]


async def getLinksFromFile(message) -> list:
    links_list = []
    text_file_dir = await message.download()
    async with aiopen(text_file_dir, "r+") as f:
        lines = await f.readlines()
        links_list.extend(line.strip() for line in lines if len(line) != 0)
    await remove(text_file_dir)
    return links_list


async def extractBulkLinks(message, bulk_start: str, bulk_end: str) -> list:
    bulk_start = int(bulk_start)
    bulk_end = int(bulk_end)
    links_list = []
    if reply_to := message.reply_to_message:
        if (file_ := reply_to.document) and (file_.mime_type == "text/plain"):
            links_list = await getLinksFromFile(reply_to)
        elif text := reply_to.text:
            links_list = getLinksFromMessage(text)
    return filterLinks(links_list, bulk_start, bulk_end) if links_list else links_list
