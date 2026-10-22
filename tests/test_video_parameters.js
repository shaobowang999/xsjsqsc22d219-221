const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function readFunction(source, name) {
    const match = source.match(new RegExp(`function ${name}\\([^]*?\\n}`));
    assert.ok(match, `Missing function ${name}`);
    return match[0];
}

for (const file of ['canvas.js', 'smart-canvas.js']) {
    const source = fs.readFileSync(path.join(__dirname, '../static/js', file), 'utf8');
    const context = vm.createContext({settings: {}, tr: key => key, escapeHtml: value => value});
    vm.runInContext(readFunction(source, 'normalizeFluxVideoResolution'), context);
    for (const [value, expected] of [['480p','hd'], ['720p','hd'], ['1080p','fhd'], ['HD','hd'], ['FHD','fhd'], ['','hd']]) {
        assert.equal(context.normalizeFluxVideoResolution('flux-3-video', value), expected, file);
    }
    assert.equal(context.normalizeFluxVideoResolution('provider/flux-3-video-fast', '1080p'), 'fhd');
    assert.equal(context.normalizeFluxVideoResolution('other-model', '480p'), '480p');
    if (file === 'smart-canvas.js') {
        vm.runInContext(readFunction(source, 'renderVideoResolutionControl'), context);
        context.settings = {videoModel: 'flux-3-video', videoResolution: '480p'};
        let html = context.renderVideoResolutionControl();
        assert.equal(context.settings.videoResolution, 'hd');
        assert.ok(html.includes('data-smart-value="hd"'));
        assert.ok(html.includes('data-smart-value="fhd"'));
        assert.ok(!html.includes('data-smart-value="480p"'));
        context.settings.videoModel = 'other-model';
        html = context.renderVideoResolutionControl();
        assert.equal(context.settings.videoResolution, '720p');
        assert.ok(html.includes('data-smart-value="480p"'));
    }
}
console.log('Video parameter UI checks passed.');
