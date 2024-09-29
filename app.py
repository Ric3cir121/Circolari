import requests, asyncio, pyrogram, prv, traceback, json, os, html

app = None

async def fileWrite(path, content):
    f = open(path, "w")
    try: f.write(content)
    except: traceback.print_exc()
    finally: f.close()

async def fileRead(path):
    content = None
    f = open(path, "r")
    try: content = f.read()
    except: traceback.print_exc()
    finally: f.close()
    return content

async def readSavedData():
    if not os.path.exists("data.json") and not os.path.exists("data.old.json"):
        return {}
    data = None
    try: data = json.loads(await fileRead("data.json"))
    except: data = json.loads(await fileRead("data.old.json"))
    return data

async def writeSavedData(data):
    if os.path.exists("data.json"):
        await fileWrite("data.old.json", await fileRead("data.json"))
    await fileWrite("data.json", json.dumps(data))

async def getCircolari():
    page = requests.get("https://www.iis-amarimercuri.edu.it/tipologia-circolare/circolari-per-alunni-e-famiglie/")
    
    if page.status_code == 200:
        content = page.content.decode()
        circolariHTML = content.split('<a class="presentation-card-link" ')[1:][::-1]
        circolari = {}
        
        for circolareHTML in circolariHTML:
            isHidden = False
            if '<p class="font-weight-bold pl-2">' in circolareHTML:
                title = "Hidden"
                isHidden = True
            else:
                title = circolareHTML.split('<h2 class="h3">')[1].split('</h2>')[0]
            
            url = None
            number = None
            description = None
            
            if not isHidden:
                url = circolareHTML.split('href="')[1].split('">')[0]
                number = circolareHTML.split('<small class="h6 text-greendark">')[1].split('</small>')[0]
                description = circolareHTML.split('<p>')[1].split('</p>')[0]
            
            if isHidden:
                continue
            
            circolareId = url.split("circolare/")[1].strip("/")
            
            circolare = {
                "id": circolareId,
                "title": title,
                "number": number,
                "description": description,
                "url": url,
                "isHidden": isHidden
            }
            circolari[circolareId] = circolare
        return circolari

async def formatCircolare(circolare):
    return (f"❇️ <a href=\"{html.escape(circolare['url'])}\"><b>{html.escape(circolare['title'])}</b></a>\n" +
            f"{html.escape(circolare['description'])}\n" +
            f"<i>{html.escape(circolare['number'])}</i>")

async def broadcastUpdate(text):
    global app
    await app.send_message(chat_id=prv.sendToChatId, text=text, parse_mode=pyrogram.enums.ParseMode.HTML)

async def circolariLoop():
    await asyncio.sleep(10)
    data = await readSavedData()
    circolari = data.get("circolari", {})
    statusCode = data.get("statusCode", 0)
    updatedStatusCode = data.get("updatedStatusCode", 0)
    failedUpdates = 0
    while True:
        newCircolari = {}
        try:
            newCircolari = await getCircolari()
            if len(newCircolari.keys()) == 0:
                updatedStatusCode = 2
            else:
                updatedStatusCode = 0
        except:
            traceback.print_exc()
            updatedStatusCode = 1
        
        if updatedStatusCode != 0:
            failedUpdates += 1
        else:
            failedUpdates = 0

        if app:
            if statusCode != updatedStatusCode and failedUpdates >= 10:
                code = [
                    "OK",
                    "EXCEPTION_ON_FETCH",
                    "EMPTY_RESULT"
                ][updatedStatusCode]
                text = [
                    "✅ Il problema è stato risolto",
                    "❌ Aggiornamento delle circolari fallito"
                ][updatedStatusCode!=0]
                
                text = text + f"\n<i>{code}</i>"
                await broadcastUpdate(text)
                
                statusCode = updatedStatusCode
                
            if updatedStatusCode == 0:
                for key in newCircolari:
                    circolare = newCircolari[key]
                    if not key in circolari:
                        circolari[key] = circolare
                        await broadcastUpdate(await formatCircolare(circolare))
                        break
        else:
            print("The app is not running...")
        
        data["circolari"] = circolari
        data["statusCode"] = statusCode
        data["updatedStatusCode"] = updatedStatusCode
        await writeSavedData(data)
        
        await asyncio.sleep(60)

async def telegramApp():
    global app
    app = pyrogram.Client("app", api_id=prv.api_id, api_hash=prv.api_hash, bot_token=prv.bot_token)
    await app.start()

async def main():
    await asyncio.gather(circolariLoop(), telegramApp())

if __name__ == "__main__":
    asyncio.run(main())
