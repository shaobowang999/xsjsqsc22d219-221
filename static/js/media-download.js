/* Shared download path for browser and pywebview canvas clients. */
window.StudioDownload = {
    async saveBlob(blob, filename){
        const url = URL.createObjectURL(blob);
        try { return await this.save(url, filename); }
        finally { URL.revokeObjectURL(url); }
    },
    async save(url, filename='image.png', saveAs=false){
        const panel = document.createElement('div');
        panel.style.cssText = 'position:fixed;right:24px;bottom:24px;z-index:100000;padding:16px;width:320px;max-width:90vw;background:#172033;color:white;border-radius:12px;box-shadow:0 8px 32px #0004;font:13px sans-serif';
        const label = document.createElement('div');
        const progress = document.createElement('progress');
        progress.style.cssText = 'width:100%;margin-top:10px';
        progress.max = 100;
        panel.append(label, progress);
        document.body.appendChild(panel);
        let writer;
        try {
            label.textContent = `准备下载：${filename}`;
            const desktop = window.pywebview?.api || window.top?.pywebview?.api;
            // Open the picker within the original user gesture.
            if(saveAs && !desktop && window.showSaveFilePicker){
                const handle = await window.showSaveFilePicker({suggestedName:filename});
                writer = await handle.createWritable();
            }
            const href = /^(data:|blob:|\/api\/download-output)/.test(url) ? url
                : `/api/download-output?url=${encodeURIComponent(url)}&name=${encodeURIComponent(filename)}`;
            const response = await fetch(href);
            if(!response.ok) throw new Error(`下载失败（${response.status}）`);
            const total = Number(response.headers.get('content-length')) || 0;
            const reader = response.body?.getReader();
            const chunks = [];
            let received = 0;
            if(reader){
                while(true){
                    const {done, value} = await reader.read();
                    if(done) break;
                    if(writer) await writer.write(value); else chunks.push(value);
                    received += value.byteLength;
                    if(total) progress.value = Math.min(99, received / total * 100);
                    label.textContent = `正在下载：${total ? Math.floor(received / total * 100) + '% · ' : ''}${(received / 1024).toFixed(0)} KB`;
                }
            } else {
                const blob = await response.blob();
                if(writer) await writer.write(blob); else chunks.push(blob);
            }
            label.textContent = '正在保存文件…';
            if(writer){
                await writer.close();
                writer = null;
                label.textContent = `已保存：${filename}`;
            } else {
                const blob = new Blob(chunks, {type:response.headers.get('content-type') || 'application/octet-stream'});
                if(desktop?.save_download){
                    const encoded = await new Promise((resolve, reject) => {
                        const fileReader = new FileReader();
                        fileReader.onload = () => resolve(fileReader.result.split(',')[1]);
                        fileReader.onerror = reject;
                        fileReader.readAsDataURL(blob);
                    });
                    const result = await desktop.save_download(encoded, filename, saveAs);
                    if(result.cancelled){ panel.remove(); return false; }
                    if(!result.ok) throw new Error(result.error || '文件保存失败');
                    label.textContent = `已保存：${result.path}`;
                } else {
                    const objectUrl = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = objectUrl;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
                    label.textContent = `已交给浏览器保存：${filename}`;
                }
            }
            progress.value = 100;
            setTimeout(() => panel.remove(), 8000);
            return true;
        } catch(error){
            if(writer) await writer.abort().catch(() => {});
            if(error.name === 'AbortError'){ panel.remove(); return false; }
            label.textContent = error.message || '下载失败，请重试';
            progress.remove();
            const close = document.createElement('button');
            close.textContent = '关闭';
            close.onclick = () => panel.remove();
            panel.appendChild(close);
            return false;
        }
    }
};
