const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../static/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]).filter(text => text.trim());
for (const script of scripts) new vm.Script(script);

function readFunction(name) {
    const match = html.match(new RegExp(`(?:async )?function ${name}\\([^]*?\\n        }`));
    assert.ok(match, `Missing function ${name}`);
    return match[0];
}

const context = vm.createContext({});
for (const name of ['versionParts', 'compareVersions']) vm.runInContext(readFunction(name), context);
assert.ok(context.compareVersions('2026.08.28', '10.21') < 0);
assert.equal(context.compareVersions('2026.10.22', '10.22'), 0);
assert.ok(context.compareVersions('2026.10.23', '10.22') > 0);
assert.equal(context.compareVersions('10.22', '2026.10.22.0'), 0);
assert.equal(context.compareVersions('2026.10.22', '2026.10.22'), 0);

async function check(current, remote, source = 'github') {
    let shown = false;
    let hidden = false;
    let notes;
    const data = {
        '/api/app-info': {version: current, update_notes: {version: current, items: ['Current changes']}},
        '/api/check-update': {current, reachable: true, latest: {source, version: remote, update_notes: {version: remote, items: ['Latest changes']}}},
    };
    Object.assign(context, {
        window: {}, document: {getElementById: () => ({classList: {remove() {}}})},
        appInfo: {}, fetch: async url => ({ok: true, json: async () => data[url]}),
        setProjectVersionBadge() {}, showUpdateNotice() {shown = true;},
        hideUpdateNotice() {hidden = true;}, setProjectUpdateNotes(value) {notes = value;},
        setUpdateSource() {},
    });
    vm.runInContext(readFunction('checkForUpdates'), context);
    await context.checkForUpdates(false);
    return {shown, hidden, notes};
}

(async () => {
    const current = await check('2026.10.22', '2026.10.22');
    assert.equal(current.shown, false);
    assert.equal(current.hidden, true);
    assert.equal(current.notes.version, '2026.10.22');
    assert.equal((await check('10.22', '2026.08.28')).shown, false);
    assert.equal((await check('10.21', '2026.10.22')).shown, true);
    assert.equal((await check('10.21', '2099.01.01', 'modelscope')).shown, false);
    assert.ok(!html.includes('Daniel8152/Infinite-Canvas'));
    console.log('Company update UI checks passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});
