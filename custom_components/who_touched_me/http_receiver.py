from aiohttp import web

async def handle_post(request):
    data = await request.json()
    request.app["hass"].bus.async_fire("ekey.fingerprint_detected", {
        "user_id": data.get("params", {}).get("userId"),
        "finger_index": data.get("params", {}).get("fingerIndex")
    })
    return web.Response(text="OK")

def start_server(hass):
    app = web.Application()
    app["hass"] = hass
    app.router.add_post("/api/notification/finger", handle_post)
    runner = web.AppRunner(app)

    async def run_app():
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 9123)
        await site.start()

    hass.loop.create_task(run_app())
