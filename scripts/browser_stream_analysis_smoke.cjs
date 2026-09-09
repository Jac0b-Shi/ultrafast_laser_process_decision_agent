// Run against disposable QA containers. Credentials and generated records are fixtures.
const {chromium}=require(process.env.CODEX_NODE_MODULES+'/playwright');
const fs=require('fs');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.addInitScript(()=>{
    Element.prototype.scrollIntoView=function(){ return Promise.resolve(); };
  });
  const page=await context.newPage();
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const base=process.env.SMOKE_BASE_URL||'http://127.0.0.1:13011';

  await page.goto(base);
  await page.getByLabel('用户名',{exact:true}).fill('qa-admin');
  await page.getByLabel('密码',{exact:true}).fill('qa-stream-password-123');
  await page.getByRole('button',{name:'登录',exact:true}).click();
  await page.getByRole('heading',{name:'今天，想先讨论什么？'}).waitFor();
  if(await page.title()!=='超快激光加工工艺数据库智能体系统')throw Error('产品标题不一致');

  const input=page.getByLabel('对话输入');
  await input.fill('数据集里有哪些材料？');
  await page.getByRole('button',{name:'发送',exact:true}).waitFor();
  await input.press('Shift+Enter');
  if(!(await input.inputValue()).endsWith('\n'))throw Error('Shift+Enter 未保留换行');
  await input.press('Enter');
  await page.getByText(/当前为本地确定性模式/).waitFor({timeout:30000});
  await page.getByText('执行过程',{exact:true}).waitFor();
  if(await page.getByText('材料与数据概况',{exact:false}).count()===0)throw Error('缺少真实工具活动');
  if(errors.length)throw Error('Promise scrollIntoView 回归：'+errors.join('; '));

  await page.getByRole('button',{name:'工艺分析',exact:true}).click();
  await page.getByRole('heading',{name:'工艺分析',exact:true}).waitFor();
  await page.getByLabel('分析材料').selectOption({label:'BF33'});
  const metric=page.getByLabel('分析指标');
  const choices=await metric.locator('option').allTextContents();
  if(choices.length<2)throw Error('BF33 没有可评估指标');
  await metric.selectOption({index:1});
  await page.getByRole('button',{name:'开始评估',exact:true}).click();
  await page.locator('summary').filter({hasText:/BF33.*完成/}).waitFor({timeout:120000});
  await page.getByText('个人模型版本',{exact:true}).waitFor();
  const enable=page.getByRole('button',{name:'启用此版本',exact:true}).first();
  await enable.click();
  await page.getByText('当前启用',{exact:true}).waitFor();
  await page.getByRole('button',{name:'恢复自动选模',exact:true}).click();
  await page.getByText('当前启用',{exact:true}).waitFor({state:'detached'});

  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:/菜单/}).click();
  await page.getByRole('button',{name:'对话推荐',exact:true}).click();
  await page.getByLabel('对话输入').scrollIntoViewIfNeeded();
  const inputBox=await page.getByLabel('对话输入').boundingBox();
  const sendBox=await page.getByRole('button',{name:'发送',exact:true}).boundingBox();
  if(!inputBox||!sendBox||Math.abs((inputBox.y+inputBox.height)-sendBox.y)>180)throw Error('手机输入区与发送按钮未保持相邻');
  if(errors.length)throw Error(errors.join('; '));

  fs.mkdirSync('.runtime-state',{recursive:true});
  await page.screenshot({path:'.runtime-state/stream-analysis-mobile.png',fullPage:true});
  fs.writeFileSync('.runtime-state/stream-analysis-browser-results.json',JSON.stringify({
    passed:true,
    checks:['登录与完整产品名','真实 SSE 完成','工具活动','Shift+Enter','scrollIntoView Promise','后台评估','版本启用与恢复自动选模','手机输入区'],
    pageErrors:errors
  },null,2));
  await browser.close();
  console.log('Streaming and analysis browser acceptance passed');
})().catch(error=>{console.error(error);process.exit(1)});
