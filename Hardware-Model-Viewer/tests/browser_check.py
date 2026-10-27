"""Offline browser rendering and expansion checks using installed Chrome or Edge."""
import json
import os
import re
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.test-deps'),str(ROOT/'src')]
from playwright.sync_api import sync_playwright, expect
from jama_model_viewer.server import handler
from jama_model_viewer.service import load_config

out=ROOT/'tests/output';out.mkdir(parents=True,exist_ok=True)
config=load_config(ROOT/'config/viewer.example.json')
server=ThreadingHTTPServer(('127.0.0.1',0),handler(config,True))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1100,'height':1000},device_scale_factor=1)
    errors=[];external=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
        if not r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/'):
            external.append(r.request.url);r.abort()
        else:r.continue_()
    page.route('**/*',route)
    page.goto(f'http://127.0.0.1:{server.server_port}/spa?demo=1')
    expect(page.locator('#status')).to_have_text(re.compile('^Model ready'),timeout=30000)
    assert page.locator('canvas').evaluate('(c)=>c.width>0&&c.height>0')
    page.locator('#animations-section > summary').click()
    page.locator('#animations .asset-card > summary').click()
    expect(page.locator('#animations img')).to_have_attribute('src',re.compile('^blob:'))
    page.get_by_role('button',name='Play',exact=True).click()
    page.wait_for_timeout(300)
    gif_src=page.locator('#animations img').get_attribute('src')
    page.get_by_role('button',name='Stop',exact=True).click()
    assert page.locator('#animations img').get_attribute('src')!=gif_src
    page.locator('#drawings-section > summary').click()
    page.locator('#drawings .asset-card > summary').click()
    expect(page.locator('#drawings img')).to_have_attribute('src',re.compile('^blob:'))
    page.get_by_role('button',name='Zoom in',exact=True).click()
    assert '125%' in page.locator('#drawings img').get_attribute('style')
    page.get_by_role('button',name='Top',exact=True).click()
    page.screenshot(path=str(out/'viewer-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('#theme').select_option('dark')
    page.screenshot(path=str(out/'viewer-mobile-dark.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'Horizontal overflow'
    page.locator('#model-section > summary').click()
    assert not page.locator('#model-section').evaluate('(e)=>e.open')
    assert not errors,errors
    assert not external,external
    (out/'browser-results.json').write_text(json.dumps({'passed':True,'pageErrors':errors,'externalRequests':external,'checks':['GLB render','GIF poster/play/stop','drawing zoom','standard camera','collapsible model','mobile dark layout','no external network']},indent=2))
    browser.close()
server.shutdown()
print('Browser checks passed without external network access.')
