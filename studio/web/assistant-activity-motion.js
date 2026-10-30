// Desktop activity artwork uses original face-and-eye characters.
// This renderer is shared by the preview-off surface and Settings samples.
import {ACTIVITY_ATLASES} from './assets/assistant-activities/atlases.js';
const actors=new Map(),images=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
let frame=0,lastDraw=0;
const MODES={computer:0,listening:1,translation:2,dubbing:3,sleep:4};
export function activitySource(atlas,scene){
 const override=atlas.sceneOverrides?.[Object.keys(MODES)[scene]],asset=override||atlas;
 const single=asset.layout==='single',cell=asset.sourceCell??scene;
 return {asset,region:single?[0,0,1,1]:[(cell%2)*.5,Math.floor(cell/2)*.5,.5,.5],exclusions:override?(asset.boundaryExclusions||[]):(atlas.boundaryExclusions?.[scene]||[])};
}
function weight(x,y,cx,cy,rx,ry){const d=((x-cx)/rx)**2+((y-cy)/ry)**2;return d>=1?0:(1-d)**3;}
const HANDS=[[[.54,.46,.13,.11],[.62,.47,.13,.11]],[[.49,.28,.13,.15],[.65,.48,.14,.12],[.52,.47,.14,.12]],[[.56,.41,.18,.15],[.65,.40,.17,.14]],[[.34,.44,.17,.17],[.31,.49,.16,.14]]];
const PERFORMANCE_HANDS={
 studio:[[.34,.38,.13,.12],[.43,.4,.12,.12]],ocean:[[.18,.33,.11,.11],[.4,.39,.11,.11]],
 energy:[[.28,.39,.12,.1],[.45,.38,.12,.1]],ninja:[[.29,.39,.12,.1],[.43,.39,.1,.1]],
 retro:[[.29,.4,.11,.11],[.42,.39,.1,.1]],forest:[[.29,.39,.11,.1],[.42,.38,.1,.1]],
 future:[[.34,.41,.11,.11],[.44,.4,.09,.11]],mint:[[.15,.17,.12,.11],[.4,.37,.11,.12]],
 moonflower:[[.28,.36,.12,.12],[.45,.36,.11,.13]]
};
function handLock(x,y,scene,theme){
 const regions=scene===3?(PERFORMANCE_HANDS[theme]||PERFORMANCE_HANDS.studio):HANDS[scene];
 return Math.max(...regions.map(([cx,cy,rx,ry])=>{
  const d=Math.sqrt(((x-cx)/rx)**2+((y-cy)/ry)**2);
  if(d<=.8)return 1;if(d>=1.4)return 0;
  const k=(d-.8)/.6;return 1-k*k*(3-2*k);
 }));
}
// Small crown-hair regions for the independent build258 poses. Keep face,
// hands, body and furniture outside the moving region.
const CROWN_HAIR={
 energy:[[.55,.075,.15,.03],[.55,.075,.15,.03],[.55,.075,.15,.03],[.50,.065,.12,.03]],
 ninja:[[.54,.10,.10,.025],[.54,.10,.10,.025],[.54,.10,.10,.025],[.45,.065,.10,.025]],
 retro:[[.53,.08,.12,.03],[.53,.08,.12,.03],[.53,.08,.12,.03],[.41,.075,.10,.025]],
 mint:[[.56,.09,.09,.025],[.56,.09,.09,.025],[.56,.09,.09,.025],[.42,.075,.08,.02]],
 moonflower:[[.59,.11,.09,.02],[.59,.11,.09,.02],[.59,.11,.09,.02],[.50,.07,.09,.02]]
};
// Rest262 has independent poses. Move only these small crown-hair patches.
export const REST_HAIR={
 studio:[.43,.105,.09,.035], ocean:[.39,.145,.10,.035],
 energy:[.67,.105,.11,.028], ninja:[.51,.080,.12,.025],
 retro:[.36,.100,.11,.027], forest:[.46,.135,.11,.028],
 future:[.52,.155,.12,.033], mint:[.44,.085,.09,.024],
 moonflower:[.50,.095,.10,.025]
};
// Each rest pose has its own head region. The central region moves rigidly,
// so breathing cannot stretch the eyes, mouth or face proportions.
export const REST_HEAD={studio:[.45,.25,.20,.19],ocean:[.37,.25,.17,.17],energy:[.66,.24,.18,.17],ninja:[.52,.24,.18,.18],retro:[.42,.23,.21,.19],forest:[.44,.27,.18,.17],future:[.53,.29,.23,.20],mint:[.40,.24,.18,.18],moonflower:[.51,.24,.18,.19]};
export function restHeadWeight(x,y,theme='studio'){
 const[cx,cy,rx,ry]=REST_HEAD[theme]||REST_HEAD.studio,d=Math.hypot((x-cx)/rx,(y-cy)/ry);
 if(d<=1)return 1;if(d>=1.45)return 0;const k=(d-1)/.45;return 1-k*k*(3-2*k);
}
export function activityPoint(x,y,t,scene,idle=false,theme='studio'){
 const region=scene===4?(REST_HAIR[theme]||REST_HAIR.studio):CROWN_HAIR[theme]?.[scene]||(scene===3?[.28,.075,.22,.055]:[.36,.085,.24,.065]);
 const hair=weight(x,y,...region);
 if(scene===4){
  const phase=Object.keys(REST_HEAD).indexOf(theme)*.37,breath=Math.sin(t*Math.PI/2.8+phase),head=restHeadWeight(x,y,theme),[cx,cy]=REST_HEAD[theme]||REST_HEAD.studio;
  const angle=.003*Math.sin(t*.72+phase),c=Math.cos(angle),s=Math.sin(angle);
  const dx=(x-cx)*(c-1)-(y-cy)*s+.001*Math.sin(t*.83+phase),dy=(x-cx)*s+(y-cy)*(c-1)-.0025*breath;
  return [.04+(x+head*dx+.003*Math.sin(t*1.13+phase)*hair)*.92,.02+(y+head*dy+.0013*Math.sin(t*.91+phase)*hair)*.90];
 }
 return [.04+(x+.0013*Math.sin(t*.8)*hair)*.92,.02+(y+.0006*Math.sin(t*.7)*hair)*.90];
}

function imageFor(theme){
 const row=ACTIVITY_ATLASES[theme]||ACTIVITY_ATLASES.studio;
 function read(asset){const key=asset.image+'?v='+asset.sha256.slice(0,12);if(!images.has(key))images.set(key,new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error('Activity image unavailable'));img.src='./assets/'+key;}));return images.get(key);}
 return Promise.all(Object.keys(MODES).map(activity=>read(row.sceneOverrides?.[activity]||row)));
}
function makeGL(canvas,sceneImages,atlas){
 const gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:true,antialias:true,preserveDrawingBuffer:true,powerPreference:'low-power'});if(!gl)return null;
 const compile=(type,text)=>{const shader=gl.createShader(type);gl.shaderSource(shader,text);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));return shader;};
 const vs=compile(gl.VERTEX_SHADER,'attribute vec2 point;attribute vec2 base;varying vec2 uv;void main(){uv=base;gl_Position=vec4(point.x*2.-1.,1.-point.y*2.,0.,1.);}');
 const fs=compile(gl.FRAGMENT_SHADER,'precision mediump float;varying vec2 uv;uniform sampler2D image;uniform vec4 region;uniform vec2 pixel;uniform vec4 exclusions[16];void main(){for(int i=0;i<16;i++){vec4 r=exclusions[i];if(uv.x>=r.x&&uv.x<r.z&&uv.y>=r.y&&uv.y<r.w)discard;}vec2 at=region.xy+clamp(uv*region.zw,pixel,region.zw-pixel);gl_FragColor=texture2D(image,at);}');
 const program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
 const side=30,base=[],triangles=[];for(let y=0;y<=side;y++)for(let x=0;x<=side;x++)base.push(x/side,y/side);
 for(let y=0;y<side;y++)for(let x=0;x<side;x++){const a=y*(side+1)+x;triangles.push(a,a+1,a+side+1,a+1,a+side+2,a+side+1);}
 const rest=new Float32Array(base),posed=new Float32Array(base.length),positions=gl.createBuffer(),textureCoords=gl.createBuffer(),indices=gl.createBuffer(),textures=new Map();
 gl.bindBuffer(gl.ARRAY_BUFFER,positions);gl.bufferData(gl.ARRAY_BUFFER,posed,gl.DYNAMIC_DRAW);const point=gl.getAttribLocation(program,'point');gl.enableVertexAttribArray(point);gl.vertexAttribPointer(point,2,gl.FLOAT,false,0,0);
 gl.bindBuffer(gl.ARRAY_BUFFER,textureCoords);gl.bufferData(gl.ARRAY_BUFFER,rest,gl.STATIC_DRAW);const coord=gl.getAttribLocation(program,'base');gl.enableVertexAttribArray(coord);gl.vertexAttribPointer(coord,2,gl.FLOAT,false,0,0);
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indices);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(triangles),gl.STATIC_DRAW);
 for(const image of new Set(sceneImages)){const texture=gl.createTexture();textures.set(image,texture);gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);}gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
 const region=gl.getUniformLocation(program,'region'),exclusions=gl.getUniformLocation(program,'exclusions[0]'),pixel=gl.getUniformLocation(program,'pixel');
 return {kind:'webgl',draw(t,scene,idle){const image=sceneImages[scene];gl.useProgram(program);gl.bindTexture(gl.TEXTURE_2D,textures.get(image));gl.uniform2f(pixel,.5/image.width,.5/image.height);const masks=new Float32Array(64).fill(-2);for(const [i,rect] of activitySource(atlas,scene).exclusions.slice(0,16).entries())masks.set(rect,i*4);gl.uniform4fv(exclusions,masks);for(let i=0;i<rest.length;i+=2){const p=activityPoint(rest[i],rest[i+1],t,scene,idle,atlas.characterId.replace('assistant-',''));posed[i]=p[0];posed[i+1]=p[1];}gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(program);gl.uniform4fv(region,activitySource(atlas,scene).region);gl.bindBuffer(gl.ARRAY_BUFFER,positions);gl.bufferSubData(gl.ARRAY_BUFFER,0,posed);gl.drawElements(gl.TRIANGLES,triangles.length,gl.UNSIGNED_SHORT,0);},dispose(){for(const texture of textures.values())gl.deleteTexture(texture);gl.deleteBuffer(positions);gl.deleteBuffer(textureCoords);gl.deleteBuffer(indices);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);gl.getExtension('WEBGL_lose_context')?.loseContext()}};
}
function make2D(canvas,sceneImages,atlas){
 const ctx=canvas.getContext('2d');if(!ctx)return null;
 // Clip the source tile before local mesh transforms, so a neighbour cannot leak.
 const tiles=Array.from({length:5},(_,scene)=>{const image=sceneImages[scene],c=document.createElement('canvas'),source=activitySource(atlas,scene),[u,v,w,h]=source.region;c.width=image.width*w;c.height=image.height*h;const tileContext=c.getContext('2d');tileContext.drawImage(image,u*image.width,v*image.height,c.width,c.height,0,0,c.width,c.height);for(const [x1,y1,x2,y2] of source.exclusions)tileContext.clearRect(Math.round(x1*c.width),Math.round(y1*c.height),Math.round((x2-x1)*c.width),Math.round((y2-y1)*c.height));return c;});
 function triangle(image,source,dest){const[a,b,c]=source,[p,q,r]=dest,det=a[0]*(b[1]-c[1])+b[0]*(c[1]-a[1])+c[0]*(a[1]-b[1]);const solve=v=>[(v[0]*(b[1]-c[1])+v[1]*(c[1]-a[1])+v[2]*(a[1]-b[1]))/det,(v[0]*(c[0]-b[0])+v[1]*(a[0]-c[0])+v[2]*(b[0]-a[0]))/det,(v[0]*(b[0]*c[1]-c[0]*b[1])+v[1]*(c[0]*a[1]-a[0]*c[1])+v[2]*(a[0]*b[1]-b[0]*a[1]))/det];const x=solve([p[0],q[0],r[0]]),y=solve([p[1],q[1],r[1]]);ctx.save();ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.lineTo(...r);ctx.closePath();ctx.clip();ctx.setTransform(x[0],y[0],x[1],y[1],x[2],y[2]);ctx.drawImage(image,0,0);ctx.restore();}
 return {kind:'canvas2d',draw(t,scene,idle){ctx.clearRect(0,0,canvas.width,canvas.height);const tile=tiles[scene],n=scene===4?16:10;for(let y=0;y<n;y++)for(let x=0;x<n;x++){const points=[[x/n,y/n],[(x+1)/n,y/n],[x/n,(y+1)/n],[(x+1)/n,(y+1)/n]],s=points.map(([u,v])=>[u*tile.width,v*tile.height]),d=points.map(([u,v])=>{const p=activityPoint(u,v,t,scene,idle,atlas.characterId.replace('assistant-',''));return[p[0]*canvas.width,p[1]*canvas.height]});triangle(tile,[s[0],s[1],s[2]],[d[0],d[1],d[2]]);triangle(tile,[s[1],s[3],s[2]],[d[1],d[3],d[2]]);}},dispose(){ctx.clearRect(0,0,canvas.width,canvas.height)}};
}
function visible(a){return a.ready&&a.visible&&a.canvas.isConnected&&!document.hidden;}
function animated(a){return visible(a)&&!a.canvas.closest('.assistant-workflow.is-paused')&&!reduced.matches;}
function draw(a,time){const scene=MODES[a.canvas.dataset.activity]??2,idle=a.canvas.closest('.assistant-workflow.is-idle');a.renderer.draw(reduced.matches||a.canvas.closest('.assistant-workflow.is-paused')?0:time,scene,!!idle);a.canvas.dataset.scene=String(scene);a.canvas.dataset.draws=String(++a.draws);}
function resize(a){const box=a.canvas.parentElement,side=Math.max(1,Math.min(box.clientWidth,box.clientHeight)),size=Math.min(960,Math.round(side*Math.min(2,devicePixelRatio||1)));a.canvas.style.width=side+'px';a.canvas.style.height=side+'px';if(a.canvas.width!==size){a.canvas.width=size;a.canvas.height=size;}if(a.ready)draw(a,performance.now()/1000);}
function schedule(){if(!frame&&[...actors.values()].some(animated))frame=requestAnimationFrame(tick);}
function tick(now){frame=0;if(now-lastDraw>=1000/30-.5){lastDraw=now;for(const a of actors.values())if(animated(a))draw(a,now/1000);}schedule();}
export function syncAssistantActivities(){
 for(const [canvas,a]of actors)if(!canvas.isConnected){a.observer.disconnect();a.resize.disconnect();a.renderer?.dispose();actors.delete(canvas);}
 for(const canvas of document.querySelectorAll('canvas.activity-art'))if(!actors.has(canvas)){
  const theme=canvas.dataset.theme in ACTIVITY_ATLASES?canvas.dataset.theme:'studio',a={canvas,ready:false,visible:false,draws:0};actors.set(canvas,a);
  a.observer=new IntersectionObserver(entries=>{a.visible=entries[0].isIntersecting;if(a.visible){resize(a);schedule();}});a.observer.observe(canvas);a.resize=new ResizeObserver(()=>{resize(a);schedule();});a.resize.observe(canvas.parentElement);
  imageFor(theme).then(img=>{if(!canvas.isConnected||!actors.has(canvas))return;try{a.renderer=makeGL(canvas,img,ACTIVITY_ATLASES[theme])||make2D(canvas,img,ACTIVITY_ATLASES[theme]);if(!a.renderer)throw Error('No scene renderer');a.ready=true;canvas.dataset.renderer=a.renderer.kind;canvas.dataset.characterId='assistant-'+theme;canvas.dataset.atlasHash=ACTIVITY_ATLASES[theme].sha256;canvas.dataset.artStyle=ACTIVITY_ATLASES[theme].artStyle||'illustrated-face-and-eyes';resize(a);schedule();}catch(e){canvas.dataset.renderer='unavailable';console.warn('Assistant scene unavailable',e.message);}}).catch(()=>{canvas.dataset.renderer='unavailable'});
 }
 for(const a of actors.values())if(a.ready&&a.visible)draw(a,performance.now()/1000);schedule();
}
reduced.addEventListener('change',()=>{if(frame)cancelAnimationFrame(frame);frame=0;for(const a of actors.values())if(a.ready)draw(a,performance.now()/1000);schedule();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&frame){cancelAnimationFrame(frame);frame=0;}else schedule();});
