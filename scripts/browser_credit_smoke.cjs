// Run against disposable QA containers; all credentials and prices below are fixtures.
const {chromium}=require(process.env.CODEX_NODE_MODULES+'/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.route('**/www.gravatar.com/**',route=>route.abort()); // Test image failure fallback.
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://localhost:13001';
 async function login(p,name,password){await p.goto(base);await p.getByLabel('用户名',{exact:true}).fill(name);await p.getByLabel('密码',{exact:true}).fill(password);await p.getByRole('button',{name:'登录',exact:true}).click();await p.getByRole('heading',{name:'这次，你想加工什么？'}).waitFor();}
 async function create(name,admin){await page.getByLabel('新用户名').fill(name);await page.getByLabel('新用户邮箱').fill(name+'@example.com');await page.getByLabel('新用户密码').fill(name+'-password-123');if(admin)await page.locator('form').filter({has:page.getByLabel('新用户名')}).getByLabel('管理员',{exact:true}).check();await page.getByRole('button',{name:'创建账号',exact:true}).click();}
 await login(page,'qa-admin','qa-isolated-password-123');
 if(await page.title()!=='超快激光加工工艺数据库智能体')throw Error('title');
 if(await page.getByRole('button',{name:'生成一组参数 ↑'}).isEnabled())throw Error('empty request');
 await page.getByRole('button',{name:'管理中心',exact:true}).click();
 await create('qa-member',false);await page.getByText(/qa-member · 用户/).waitFor();
 await create('qa-manager',true);await page.getByRole('button',{name:'登录',exact:true}).waitFor();
 await login(page,'qa-manager','qa-manager-password-123');
 const blocked=await context.request.post(base+'/api/agent/login',{data:{username:'qa-admin',password:'qa-isolated-password-123'}});if(blocked.status()!==401)throw Error('bootstrap still active');
 await page.getByRole('button',{name:'管理中心',exact:true}).click();
 const member=page.locator('details').filter({has:page.locator('summary').filter({hasText:'qa-member · 用户'})});
 await member.locator('summary').click();await member.getByLabel('信用额度 / credit').fill('5');await member.getByRole('button',{name:'保存账号设置'}).click();await page.getByText(/账号配置已保存/).waitFor();
 await member.getByPlaceholder('追加 credit').fill('10');await member.getByPlaceholder('充值原因／凭据说明').fill('browser fixture');await member.getByRole('button',{name:'追加额度'}).click();await page.getByText('额度已入账。',{exact:true}).waitFor();
 await page.getByRole('button',{name:'大语言模型',exact:true}).click();
 await page.getByLabel('显示名称',{exact:true}).fill('QA metered model');await page.getByLabel('服务地址',{exact:true}).fill('http://localhost:9001/v1');await page.getByLabel('模型标识',{exact:true}).fill('fixture');await page.getByLabel('API Key',{exact:true}).fill('fixture-secret');
 for(const [kind,prices] of [['cost',[1,2,3]],['sale',[2,4,6]]])for(const [i,k]of ['cached','uncached','output'].entries())await page.getByLabel(kind+' '+k,{exact:true}).fill(String(prices[i]));
 await page.getByLabel('启用',{exact:true}).check();await page.getByLabel('默认模型',{exact:true}).check();await page.getByRole('button',{name:'保存模型'}).click();await page.getByRole('button',{name:'QA metered model · v1',exact:true}).click();
 if(await page.getByLabel('API Key',{exact:true}).inputValue())throw Error('key echoed');
 await page.getByRole('button',{name:'测试连接'}).click();await page.getByText(/模型连通性测试通过/).waitFor();
 await page.getByRole('button',{name:'激活码',exact:true}).click();await page.getByLabel('指定激活码（可选）').fill('BROWSER-CREDIT-CODE');await page.getByLabel('每次到账 credit').fill('25');await page.getByLabel('每码总核销次数').fill('2');await page.getByRole('button',{name:'生成激活码',exact:true}).click();await page.getByRole('button',{name:'下载领取文件'}).waitFor();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'下载领取文件'}).click();await (await downloadPromise).saveAs('.runtime-state/qa-credit-codes.csv');
 const second=await browser.newContext({viewport:{width:1365,height:960}});await second.route('**/www.gravatar.com/**',route=>route.abort());const user=await second.newPage();user.on('pageerror',e=>errors.push(e.message));await login(user,'qa-member','qa-member-password-123');
 if(await user.getByRole('button',{name:'管理中心',exact:true}).count())throw Error('admin menu exposed');
 await user.getByRole('button',{name:'余额与消费',exact:true}).click();await user.getByText('10.000000 credit',{exact:true}).waitFor();await user.getByLabel('激活码',{exact:true}).fill('BROWSER-CREDIT-CODE');await user.getByRole('button',{name:'核销',exact:true}).click();await user.getByText('35.000000 credit',{exact:true}).waitFor();
 await user.getByRole('button',{name:'＋ 新的加工任务',exact:true}).click();await user.getByLabel('加工需求').fill('BF33 depth 10 μm with tolerance 100 μm');await user.getByRole('button',{name:'从描述填写目标'}).click();await user.getByText(/测试目标已提取/).waitFor();
 await user.getByRole('button',{name:'生成一组参数 ↑'}).click();await user.getByRole('heading',{name:/第 1 轮/}).waitFor({timeout:60000});
 await user.getByRole('button',{name:'余额与消费',exact:true}).click();await user.getByText('34.954000 credit',{exact:true}).waitFor();
 const calls=await (await second.request.get(base+'/api/agent/wallet/calls')).json();if(calls.length!==1||calls[0].charged_credit!==.046)throw Error('history branch should be free');
 for(const path of ['/api/agent/admin/models','/api/agent/admin/costs','/api/agent/users'])if((await second.request.get(base+path)).status()!==403)throw Error('admin isolation '+path);
 await user.locator('summary').filter({hasText:'AI 操作消费明细'}).click();await user.screenshot({path:'.runtime-state/credit-wallet.png',fullPage:true});
 await page.getByRole('button',{name:'成本统计',exact:true}).click();await page.getByRole('button',{name:'查询统计'}).click();await page.getByText('0.00046',{exact:true}).first().waitFor();await page.screenshot({path:'.runtime-state/credit-admin.png',fullPage:true});
 const csv=await context.request.get(base+'/api/agent/admin/costs?format=csv');if(!csv.ok()||!(await csv.text()).includes('charged_credit'))throw Error('cost csv');
 const users=await (await context.request.get(base+'/api/agent/users')).json();const id=users.find(u=>u.username==='qa-member').id;
 await context.request.patch(base+'/api/agent/users/'+id,{data:{enabled:false}});if((await second.request.get(base+'/api/agent/me')).status()!==401)throw Error('disabled session');
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('.runtime-state/credit-browser-results.json',JSON.stringify({passed:true,checks:['bootstrap transition','accounts','credit limit','recharge','model encrypted key','model platform test','activation code file','user redemption','paid interpretation','free history recommendation','own billing','admin isolation','disabled session','avatar fallback','CSV'],pageErrors:errors},null,2));
 await browser.close();console.log('Credit browser acceptance passed');
})().catch(e=>{console.error(e);process.exit(1)});
