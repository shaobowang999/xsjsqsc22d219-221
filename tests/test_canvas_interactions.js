const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');

(async () => {
    const browser = await chromium.launch({headless:true, channel:'msedge'});
    const context = await browser.newContext({viewport:{width:1440, height:900}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('http://canvas.test/**', async route => {
        const url = new URL(route.request().url());
        if(url.pathname.startsWith('/api/')){
            const canvas = {id:'test', title:'Test', project:'default', nodes:[], connections:[], viewport:{x:0,y:0,scale:1}};
            const data = {canvas, canvases:[], projects:[{id:'default',name:'默认项目'}], workflows:[], categories:[], libraries:[], items:[], files:[], missing:[]};
            return route.fulfill({json:data});
        }
        const file = path.join(root, decodeURIComponent(url.pathname));
        if(!fs.existsSync(file) || !fs.statSync(file).isFile()) return route.fulfill({status:404,body:''});
        const ext = path.extname(file);
        return route.fulfill({body:fs.readFileSync(file), contentType:({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'})[ext] || 'application/octet-stream'});
    });
    try {
        await page.goto('http://canvas.test/static/canvas-list.html');
        await page.locator('#newCanvasBtn').click();
        const card = page.locator('.ws-create-card');
        const board = await page.locator('#board').boundingBox();
        const initial = await card.boundingBox();
        assert.ok(Math.abs(initial.x - board.x - 16) <= 2);
        assert.ok(Math.abs(initial.y - board.y - 16) <= 2);
        const title = await card.locator('.ws-create-title').boundingBox();
        await page.mouse.move(title.x+20,title.y+8);
        await page.mouse.down();
        await page.mouse.move(title.x+200,title.y+110,{steps:8});
        await page.mouse.up();
        const moved = await card.boundingBox();
        assert.ok(moved.x > initial.x+150 && moved.y > initial.y+80);
        await card.locator('input').fill('可选择和编辑');
        assert.equal(await card.locator('input').inputValue(),'可选择和编辑');

        for(const smart of [false,true]){
            await page.goto(`http://canvas.test/static/${smart?'smart-canvas':'canvas'}.html?id=test`);
            await page.waitForFunction(() => canvas?.id === 'test');
            await page.evaluate(smart => {
                nodes = [
                    {id:'a',type:smart?'smart-image':'image',x:100,y:180,url:'',images:[],w:220,h:180},
                    {id:'b',type:smart?'smart-image':'image',x:450,y:180,url:'',images:[],w:220,h:180}
                ];
                viewport = {x:0,y:0,scale:1}; applyViewport();
                if(smart){ selectedIds = []; selectedId = ''; }
                else selected.clear();
                undoStack.length = 0; render();
            },smart);
            await page.mouse.move(70,150); await page.mouse.down();
            await page.mouse.move(710,390,{steps:8}); await page.mouse.up();
            assert.equal(await page.evaluate(smart => smart ? selectedIds.length : selected.size,smart),2);
            const selector = smart ? '.image-node[data-id="a"]' : '.node[data-id="a"] .node-head';
            const box = await page.locator(selector).boundingBox();
            await page.keyboard.down('Alt');
            await page.mouse.move(box.x+50, box.y+12);
            await page.mouse.down();
            await page.mouse.move(box.x+170,box.y+102,{steps:8});
            await page.mouse.up();
            await page.keyboard.up('Alt');
            let result = await page.evaluate(() => nodes.map(n => ({id:n.id,x:n.x,y:n.y})));
            assert.equal(result.length,4,`copy count (smart=${smart})`);
            assert.equal(result[0].x,100); assert.equal(result[1].x,450);
            assert.equal(result[2].x,220); assert.equal(result[3].x,570);
            await page.keyboard.press('Control+z');
            assert.equal(await page.evaluate(() => nodes.length),2,`one undo removes copies (smart=${smart})`);
            // Clicking alone must not consume a canvas undo action.
            if(!smart){
                await page.mouse.move(150,192); await page.mouse.down();
                await page.mouse.move(190,222,{steps:4}); await page.mouse.up();
                await page.keyboard.press('Control+z');
                assert.equal(await page.evaluate(() => nodes[0].x),100);
            }
        }
        await page.evaluate(() => {
            nodes[0].images = [{url:'/test.png',name:'test.png'}]; render();
        });
        await page.locator('.image-node[data-id="a"]').click({button:'right',position:{x:30,y:30}});
        assert.deepEqual(await page.locator('#smartImageContextMenu button').allTextContents(),['预览','编辑','替换','保存','另存为','删除']);
        await page.goto('http://canvas.test/static/canvas.html?id=test');
        await page.waitForFunction(() => canvas?.id === 'test');
        await page.evaluate(() => {
            nodes = [{id:'image',type:'image',x:100,y:100,url:'/test.png',name:'test.png'}]; render();
            openImageNodeMenu('image',200,200);
        });
        assert.deepEqual(await page.locator('#imageNodeMenu button').allTextContents(),['预览','编辑','替换','保存','另存为','删除']);
        await page.evaluate(() => {
            nodes = [{id:'out',type:'output',x:100,y:100,images:['/test.png']}]; render();
            openOutputImageMenu(nodes[0],'/test.png',200,200);
        });
        assert.deepEqual(await page.locator('#imageNodeMenu button').allTextContents(),['预览','编辑','替换','保存','另存为','删除']);
        page.once('dialog', dialog => dialog.accept());
        await page.locator('#imageNodeMenu button').last().click();
        assert.equal(await page.evaluate(() => nodes[0].images.length),0);
        await page.keyboard.press('Control+z');
        assert.equal(await page.evaluate(() => nodes[0].images.length),1);
        await page.evaluate(() => {
            window.pywebview = {api:{save_download:async (data,name,saveAs) => {
            window.savedDownload = {data,name,saveAs:Boolean(saveAs)}; return {ok:true,path:'Downloads/test.png'};
            }}};
        });
        assert.equal(await page.evaluate(() => StudioDownload.save('data:image/png;base64,aGVsbG8=','test.png')),true);
        assert.deepEqual(await page.evaluate(() => window.savedDownload),{data:'aGVsbG8=',name:'test.png',saveAs:false});
        assert.ok((await page.locator('body').innerText()).includes('已保存：Downloads/test.png'));
        assert.deepEqual(errors,[]);
        console.log('Canvas dialog, multi-node Alt drag, undo, context menus and download checks passed.');
    } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
