const {chromium, expect} = await import(process.env.PLAYWRIGHT_MODULE || '@playwright/test');
import {mkdtempSync, mkdirSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve, dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const cli = resolve(dirname(fileURLToPath(import.meta.url)), '../scripts/kanban.py');
const state = mkdtempSync(join(tmpdir(), 'agent-kanban-browser-'));
const output = resolve(process.argv[2] || 'kanban-browser-results');
mkdirSync(output, {recursive:true});
const run = (...args) => JSON.parse(execFileSync('python3', [cli,'--state',state,'--actor','lead',...args], {encoding:'utf8'}));
const bg = page => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const noOverflow = page => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
let browser;
try {
  run('init','--title','Example test board','--goal','Synthetic tasks for verifying the read-only board.');
  const names = ['Prepare the task overview','Verify task data','Review task descriptions','Inspect the blocked task','Complete the example review'];
  for (let i=0;i<5;i++) run('add',`task-0${i+1}`,'--title',names[i],'--description','A bounded outcome with an assigned agent, clear acceptance criteria, and recorded evidence.','--assignee',i%2?'implementation agent':'lead','--reviewer','lead','--criterion','The agreed observable behavior works.','--priority',i===0?'high':'normal');
  run('claim','task-02');
  run('edit','task-02','--description','Verify the sample task information is displayed accurately. Check the recorded fields, inspect the example evidence, and record the result before requesting review.','--criterion','Every recorded field remains visible in the sample task details.','--criterion','The sample board displays clear loading and failure states.','--criterion','Record example verification evidence and note any remaining review steps.','--evidence','docs/example-evidence.md','--priority','high');
  run('move','task-03','--status','in_review','--evidence','Focused checks passed; awaiting lead review.');
  run('move','task-04','--status','blocked','--blocker','Waiting for an example review response.');
  run('move','task-05','--status','done','--evidence','Lead inspected the source and the focused browser check passed.');
  run('add','task-06','--title','<img src=x onerror=alert(1)>','--description','Literal untrusted text must never become markup.','--assignee','implementation agent');
  for (let i=7;i<=12;i++) {
    const id = `task-${String(i).padStart(2,'0')}`;
    run('add',id,'--title',`Verify example checkpoint ${i-6}`,'--assignee','lead','--description','Full completed task content remains available in its details.');
    run('move',id,'--status','done','--evidence','Lead verified the example checkpoint.');
  }
  run('add','task-13','--title','Document the sample workflow','--description','Keep the example instructions aligned with the sample task.','--depends-on','task-05','--assignee','lead');
  run('add','task-14','--title','Verify narrow screens and unusually long task titles remain readable without losing any task content or hiding the task inspection controls');
  for (const [id,title] of [['task-15','Inspect the sample task history'],['task-16','Verify the sample task criteria']]) {
    run('add',id,'--title',title,'--assignee','lead','--description','Keep the outcome focused and record independent verification evidence.');
    run('claim',id);
  }
  run('add','task-17','--title','Validate the example evidence','--assignee','lead','--description','Inspect the evidence recorded for this example task.');
  run('move','task-17','--status','blocked','--blocker','Waiting for an example evidence document.');
  run('board','--summary','Agents update this board as work moves from planning through review.');
  const server=run('start','--port','0');
  run('edit','task-02','--evidence',`${server.local_url}/health`);
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1600,height:1100},colorScheme:'light'});
  const errors=[], mutations=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{ if(!['GET','HEAD'].includes(r.method())) mutations.push(`${r.method()} ${r.url()}`); });
  await page.goto(server.local_url);
  await expect(page.locator('.connection')).toContainText('Live');
  await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('.column')).toHaveCount(5);
  await expect(page.locator('.card')).toHaveCount(14);
  await expect(page.locator('#completion-label')).toHaveText('7 / 17');
  await expect(page.locator('img')).toHaveCount(0);
  await expect(page.locator('[draggable="true"],textarea,[contenteditable="true"],input[type="checkbox"]')).toHaveCount(0);
  const task = page.getByRole('button',{name:'task-02: Verify task data',exact:true});
  for (const theme of ['light','dark']) {
    await page.emulateMedia({colorScheme:theme});
    await expect.poll(()=>bg(page)).toBe(theme==='light'?'rgb(245, 247, 250)':'rgb(13, 16, 20)');
    await expect.poll(()=>page.locator('[data-task-id="task-05"]').evaluate(n=>getComputedStyle(n).backgroundColor)).toBe(theme==='light'?'rgb(255, 255, 255)':'rgb(23, 28, 35)');
    await task.focus();
    await page.screenshot({path:join(output,`${theme}-board.png`),fullPage:true});
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveAccessibleName('Verify task data');
    await expect(page.locator('#detail-criteria li')).toHaveCount(3);
    await expect(page.locator('#detail-evidence a')).toHaveCount(1);
    await expect(page.locator('#detail-evidence')).toContainText('docs/example-evidence.md');
    await expect(page.locator('#detail-evidence > div')).toContainText('Recorded reference');
    await expect(page.locator('#detail-properties')).toContainText('Not recorded');
    await expect(page.locator('#close-detail')).toBeFocused();
    await page.screenshot({path:join(output,`${theme}-detail.png`)});
    await page.keyboard.press('Shift+Tab');
    await expect(page.locator('#detail-evidence a')).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.locator('#close-detail')).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await expect(task).toBeFocused();
  }
  await task.click();
  const popupPromise=page.waitForEvent('popup');
  await page.locator('#detail-evidence a').click();
  const evidencePage=await popupPromise;
  await evidencePage.waitForLoadState();
  await expect(evidencePage.locator('body')).toContainText('instance');
  await evidencePage.close();
  for (const theme of ['light','dark','no-preference']) {
    await page.emulateMedia({colorScheme:theme});
    await expect.poll(()=>bg(page)).toBe(theme==='dark'?'rgb(13, 16, 20)':'rgb(245, 247, 250)');
    await expect.poll(()=>page.locator('#detail').evaluate(n=>getComputedStyle(n).backgroundColor)).toBe(theme==='dark'?'rgb(22, 27, 34)':'rgb(255, 255, 255)');
  }
  await page.locator('#close-detail').click();
  await expect(task).toBeFocused();
  await task.click();
  await page.mouse.click(5,5);
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('searchbox').fill('blocked task');
  await expect(page.locator('.card')).toHaveCount(1);
  await page.getByRole('searchbox').fill('task-06');
  await expect(page.locator('.card')).toHaveCount(1);
  await page.getByRole('searchbox').fill('implementation agent');
  await expect(page.locator('.card')).toHaveCount(2);
  await page.getByRole('searchbox').fill('');
  await page.getByRole('combobox').selectOption('implementation agent');
  await expect(page.locator('.card')).toHaveCount(2);
  await page.getByRole('searchbox').fill('task-06');
  await expect(page.locator('.card')).toHaveCount(1);
  await page.getByRole('searchbox').fill('missing task');
  await expect(page.locator('.card')).toHaveCount(0);
  await expect(page.locator('.empty')).toHaveCount(5);
  await page.getByRole('searchbox').fill('');
  await page.getByRole('combobox').selectOption('');
  await page.getByRole('button',{name:'View 3 more completed'}).click();
  await expect(page.locator('.column.done .card')).toHaveCount(7);
  await expect(page.locator('[data-task-id="task-10"]')).toBeFocused();
  await page.getByRole('searchbox').fill('checkpoint 6');
  await expect(page.locator('.card')).toHaveCount(1);
  await page.getByRole('searchbox').fill('');
  run('claim','task-01');
  await expect(page.locator('.column.in_progress .card')).toHaveCount(4,{timeout:10000});
  await page.getByRole('button',{name:'Activity',exact:true}).click();
  await expect(page.locator('#activity')).toContainText('Claimed work');
  await page.locator('#activity').evaluate(n=>n.scrollTop=80);
  run('board','--summary','A new orchestration update.');
  await expect(page.locator('#summary')).toContainText('A new orchestration update.',{timeout:10000});
  expect(await page.locator('#activity').evaluate(n=>n.scrollTop)).toBe(80);
  await page.getByRole('button',{name:'Activity',exact:true}).click();

  // Real CLI refresh while a task is open: preserve filters, focus and scroll.
  await page.getByRole('searchbox').fill('task-');
  await page.getByRole('combobox').selectOption('lead');
  await page.setViewportSize({width:900,height:650});
  await page.locator('#board').evaluate(n=>n.scrollLeft=250);
  await task.click();
  await page.locator('#detail-evidence a').focus();
  await page.locator('#detail-body').evaluate(n=>n.scrollTop=120);
  const scrollBefore=await page.locator('#board').evaluate(n=>n.scrollLeft);
  const columnScrollBefore=await page.locator('.in_progress .cards').evaluate(n=>n.scrollTop);
  const pageScrollBefore=await page.evaluate(()=>scrollY);
  const revision=run('edit','task-02','--description','Updated description received during inspection.','--note','Verified live refresh continuity.').revision;
  await expect(page.locator('#detail-revision')).toHaveText(`Revision ${revision}`,{timeout:10000});
  await expect(page.locator('#detail-description')).toHaveText('Updated description received during inspection.');
  await expect(page.locator('#detail-evidence a')).toBeFocused();
  expect(await page.locator('#detail-body').evaluate(n=>n.scrollTop)).toBe(120);
  expect(await page.locator('#board').evaluate(n=>n.scrollLeft)).toBe(scrollBefore);
  expect(await page.locator('.in_progress .cards').evaluate(n=>n.scrollTop)).toBe(columnScrollBefore);
  expect(await page.evaluate(()=>scrollY)).toBe(pageScrollBefore);
  await expect(page.getByRole('searchbox')).toHaveValue('task-');
  await expect(page.getByRole('combobox')).toHaveValue('lead');
  await expect(page.locator('body')).toHaveClass('modal-open');
  await page.keyboard.press('Escape');
  await expect(task).toBeFocused();
  await page.getByRole('searchbox').fill('');
  await page.getByRole('combobox').selectOption('');

  for (const width of [390,320]) {
    await page.setViewportSize({width,height:844});
    for (const theme of ['light','dark']) {
      await page.emulateMedia({colorScheme:theme});
      await page.locator('#board').evaluate(n=>n.scrollLeft=0);
      await page.screenshot({path:join(output,`${theme}-mobile-${width}.png`),fullPage:true});
      expect(await noOverflow(page)).toBe(true);
      await page.locator('.column.blocked').scrollIntoViewIfNeeded();
      await page.getByRole('button',{name:'task-04: Inspect the blocked task',exact:true}).click();
      await expect(page.getByRole('dialog')).toContainText('Waiting for an example review response.');
      await expect(page.locator('#close-detail')).toBeInViewport();
      const box=await page.getByRole('dialog').boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x+box.width).toBeLessThanOrEqual(width);
      const pageY=await page.evaluate(()=>scrollY);
      await page.mouse.move(2,400);
      await page.mouse.wheel(0,400);
      expect(await page.evaluate(()=>scrollY)).toBe(pageY);
      await page.screenshot({path:join(output,`${theme}-mobile-detail-${width}.png`)});
      await page.locator('.readonly-note').scrollIntoViewIfNeeded();
      await expect(page.locator('.readonly-note')).toBeInViewport();
      await expect(page.locator('#close-detail')).toBeInViewport();
      expect(await page.locator('#detail-body').evaluate(n=>n.scrollWidth<=n.clientWidth)).toBe(true);
      await page.keyboard.press('Escape');
    }
  }
  await page.context().setOffline(true);
  await expect(page.locator('.connection')).toContainText('Disconnected',{timeout:12000});
  await expect(page.locator('.card')).toHaveCount(17);
  await page.context().setOffline(false);
  await expect(page.locator('.connection')).toContainText('Live',{timeout:12000});
  run('board','--mode','paused','--summary','Work paused at the usage checkpoint.');
  await expect(page.locator('#summary')).toContainText('Paused',{timeout:10000});

  // Missing/unsupported preferences do not depend on matchMedia or JS theme state.
  const fallback=await browser.newPage({viewport:{width:1600,height:1100},colorScheme:'dark'});
  await fallback.addInitScript(()=>{ window.matchMedia=undefined; });
  await fallback.route('**/style.css',async route=>{
    const response=await route.fetch();
    await route.fulfill({response,body:(await response.text()).replace('prefers-color-scheme: dark','unsupported-color-scheme: dark')});
  });
  await fallback.goto(server.local_url);
  await expect(fallback.locator('.connection')).toContainText('Live');
  expect(await bg(fallback)).toBe('rgb(245, 247, 250)');
  await fallback.close();

  // Exercise unavailable tasks and empty/error states without mutating the store.
  const snapshot=run('list');
  await page.route('**/api/board',route=>route.fulfill({json:snapshot}));
  const unusual={id:'long-'.repeat(12)+'task',title:'A task with a long ID and missing optional metadata',status:'backlog',revision:1,evidence:['javascript:alert(1)','docs/missing.md']};
  snapshot.tasks.push(unusual);
  await page.getByRole('searchbox').fill(unusual.id);
  await expect(page.locator('.card')).toHaveCount(1,{timeout:10000});
  await page.locator('.card').click();
  await expect(page.locator('#close-detail')).toBeInViewport();
  await expect(page.locator('#detail-evidence a')).toHaveCount(0);
  await expect(page.locator('#detail-body')).toContainText('No additional description.');
  expect(await page.locator('#detail').evaluate(n=>n.scrollWidth<=n.clientWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await page.getByRole('searchbox').fill('');
  await task.click();
  snapshot.tasks=snapshot.tasks.filter(t=>t.id!=='task-02');
  await expect(page.getByRole('dialog')).toContainText('Task unavailable',{timeout:10000});
  await expect(page.locator('#close-detail')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('searchbox')).toBeFocused();
  snapshot.tasks=[];
  await expect(page.locator('#completion-label')).toHaveText('0 / 0',{timeout:10000});
  await expect(page.locator('.empty')).toHaveCount(5);
  const unavailable=await browser.newPage();
  await unavailable.route('**/api/board',route=>route.fulfill({status:503,body:'Unavailable'}));
  await unavailable.goto(server.local_url);
  await expect(unavailable.locator('#title')).toHaveText('Board unavailable');
  await unavailable.unroute('**/api/board');
  await expect(unavailable.locator('.connection')).toContainText('Live',{timeout:10000});
  await unavailable.close();
  expect(mutations).toEqual([]);
  expect(errors).toEqual([]);
  writeFileSync(join(output,'browser.json'),JSON.stringify({passed:true,checks:['five open columns','read-only controls and GET requests','literal task text','real evidence links','search and combined filter','completed reveal','empty and missing tasks','keyboard dialog and focus restoration','refresh preserves viewing context','activity','light/dark desktop and mobile','live system theme changes','unsupported preference fallback','mobile scrolling and fixed close control','background scroll lock','disconnected stale view and recovery','paused mode'],consoleErrors:errors},null,2)+'\n');
  console.log('Browser checks passed; screenshots saved.');
} finally {
  await browser?.close();
  run('stop');
  rmSync(state,{recursive:true,force:true});
}
