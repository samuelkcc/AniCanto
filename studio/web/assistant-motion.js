import {ASSISTANT_RIGS} from './assets/assistant-rigs.js';

// A single aligned drawing is skinned continuously at the shoulders, neck and
// ankle. No pose swaps, scale changes, crossfades or moving whole-body cutouts.
export const CYCLE=12;
const smooth=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t)};
const band=(a,b,c,d,x)=>smooth(a,b,x)*(1-smooth(c,d,x));
export function joints(seconds,activity='idle'){
 const t=seconds*2*Math.PI;
 const work={computer:[.035,.04,1.3],listening:[.09,.035,2.3],translation:[.035,.065,2],dubbing:[.07,.11,1.5]}[activity];
 return {left:(work?.[0]??.105)*Math.sin(t/(work?.[2]??3)),right:(work?.[1]??.065)*Math.sin(t/(work?.[2]??4)),head:.028*Math.sin(t/(activity==='listening'?3:6)),ankle:activity==='idle'?.07*(1-Math.cos(t/4)):.008*(1-Math.cos(t/4)),tap:.007*Math.sin(t/(activity==='translation'?1:1.5)),breath:.0035*Math.sin(t/3)};
};
export function deform(u,v,pose,rig){
 const aspect=rig.rect[2]/rig.rect[3],center=(rig.anchorX+.5)/2;
 let dx=0,dy=0;
 const rotate=(px,py,angle,weight)=>{const x=(u-px)*aspect,y=v-py,c=Math.cos(angle),s=Math.sin(angle);dx+=(x*c-y*s-x)*weight/aspect;dy+=(x*s+y*c-y)*weight;};
 const skin=rig.skin||{},shoulder=skin.shoulderY??.27,neck=skin.neckY??.25;
 const upper=band(...(skin.armBand||[.21,.32,.54,.65]),v);
 rotate(center-.12,shoulder,pose.left*(skin.armGain??1),upper*(1-smooth(center-.02,center+.12,u)));
 rotate(center+.12,shoulder,pose.right*(skin.armGain??1),upper*smooth(center-.10,center+.04,u));
 rotate(center,neck,pose.head,(1-smooth(...(skin.headBand||[.16,.27]),v))*band(0,.1,.9,1,u));
 // The left foot and hip remain planted. Only the right ankle taps.
 rotate(rig.anchorX+.10,.88,-pose.ankle,smooth(.84,.94,v)*smooth(rig.anchorX,rig.anchorX+.12,u));
 dy+=pose.tap*(skin.wristGain??1)*band(...(skin.wristBand||[.34,.43,.52,.59]),v)*(1-smooth(center-.02,center+.10,u));
 dy+=pose.breath*band(...(skin.breathBand||[.23,.35,.57,.65]),v);
 return [.5+(u+dx-rig.anchorX)*aspect*.80,.10+(v+dy)*.80];
}

const images=new Map(),actors=new Map(),motion=matchMedia('(prefers-reduced-motion: reduce)');
let timer=0,lastFrame=-Infinity;
function imageFor(rig){const key=rig.image+'?v='+rig.sha256.slice(0,12);if(!images.has(key))images.set(key,new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src='./assets/'+key}));return images.get(key)}
const VERT='attribute vec2 p;attribute vec2 uv;varying vec2 tex;void main(){tex=uv;gl_Position=vec4(p.x*2.0-1.0,1.0-p.y*2.0,0.0,1.0);}';
const FRAG='precision mediump float;varying vec2 tex;uniform sampler2D art;void main(){gl_FragColor=texture2D(art,tex);}';
function makeGL(canvas,image,rig){
 const gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:true,antialias:true,preserveDrawingBuffer:true,powerPreference:'low-power'});if(!gl)return null;
 const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
 const program=gl.createProgram(),vs=shader(gl.VERTEX_SHADER,VERT),fs=shader(gl.FRAGMENT_SHADER,FRAG);gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
 const columns=20,rows=30,vertices=[],uv=[],indices=[];
 for(let y=0;y<=rows;y++)for(let x=0;x<=columns;x++){vertices.push(x/columns,y/rows);uv.push((rig.rect[0]+x/columns*rig.rect[2])/rig.imageSize[0],(rig.rect[1]+y/rows*rig.rect[3])/rig.imageSize[1]);}
 for(let y=0;y<rows;y++)for(let x=0;x<columns;x++){const a=y*(columns+1)+x,b=a+1,c=a+columns+1,d=c+1;indices.push(a,b,c,b,d,c);}
 const rest=new Float32Array(vertices),positions=new Float32Array(vertices.length),buffer=gl.createBuffer(),texBuffer=gl.createBuffer(),indexBuffer=gl.createBuffer(),texture=gl.createTexture();
 gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,positions,gl.DYNAMIC_DRAW);const p=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(p);gl.vertexAttribPointer(p,2,gl.FLOAT,false,0,0);
 gl.bindBuffer(gl.ARRAY_BUFFER,texBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(uv),gl.STATIC_DRAW);const t=gl.getAttribLocation(program,'uv');gl.enableVertexAttribArray(t);gl.vertexAttribPointer(t,2,gl.FLOAT,false,0,0);
 gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
 gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
 return {draw(seconds){const pose=joints(seconds,canvas.dataset.activity||'idle');for(let i=0;i<rest.length;i+=2){const xy=deform(rest[i],rest[i+1],pose,rig);positions[i]=xy[0];positions[i+1]=xy[1];}gl.viewport(0,0,canvas.width,canvas.height);gl.clear(gl.COLOR_BUFFER_BIT);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,positions);gl.drawElements(gl.TRIANGLES,indices.length,gl.UNSIGNED_SHORT,0);},dispose(){gl.deleteTexture(texture);gl.deleteBuffer(buffer);gl.deleteBuffer(texBuffer);gl.deleteBuffer(indexBuffer);gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);gl.getExtension('WEBGL_lose_context')?.loseContext()}};
}
function make2D(canvas,image,rig){
 const ctx=canvas.getContext('2d'),columns=8,rows=12;if(!ctx)return null;
 function triangle(src,dst){const [a,b,c]=src,[p,q,r]=dst;const det=a[0]*(b[1]-c[1])+b[0]*(c[1]-a[1])+c[0]*(a[1]-b[1]);if(Math.abs(det)<1e-7)return;
 const solve=values=>[(values[0]*(b[1]-c[1])+values[1]*(c[1]-a[1])+values[2]*(a[1]-b[1]))/det,(values[0]*(c[0]-b[0])+values[1]*(a[0]-c[0])+values[2]*(b[0]-a[0]))/det,(values[0]*(b[0]*c[1]-c[0]*b[1])+values[1]*(c[0]*a[1]-a[0]*c[1])+values[2]*(a[0]*b[1]-b[0]*a[1]))/det];
 const x=solve([p[0],q[0],r[0]]),y=solve([p[1],q[1],r[1]]);ctx.save();ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.lineTo(...r);ctx.closePath();ctx.clip();ctx.setTransform(x[0],y[0],x[1],y[1],x[2],y[2]);ctx.drawImage(image,0,0);ctx.restore();}
 return {draw(seconds){ctx.clearRect(0,0,canvas.width,canvas.height);const pose=joints(seconds,canvas.dataset.activity||'idle'),point=(u,v)=>{const xy=deform(u,v,pose,rig);return [xy[0]*canvas.width,xy[1]*canvas.height]},source=(u,v)=>[rig.rect[0]+u*rig.rect[2],rig.rect[1]+v*rig.rect[3]];
 for(let y=0;y<rows;y++)for(let x=0;x<columns;x++){const uv=[[x/columns,y/rows],[(x+1)/columns,y/rows],[x/columns,(y+1)/rows],[(x+1)/columns,(y+1)/rows]],s=uv.map(p=>source(...p)),d=uv.map(p=>point(...p));triangle([s[0],s[1],s[2]],[d[0],d[1],d[2]]);triangle([s[1],s[3],s[2]],[d[1],d[3],d[2]]);}},dispose(){ctx.clearRect(0,0,canvas.width,canvas.height)}};
}
function visible(actor){return actor.ready&&actor.visible&&actor.canvas.isConnected&&(actor.canvas.closest('.video-stage')?.classList.contains('preview-off')||!!actor.canvas.closest('.welcome-startup')||!!actor.canvas.closest('.assistant-preview'))&&!document.hidden}
function animated(actor){return visible(actor)&&!actor.canvas.closest('.assistant-workflow.is-resting')}
function schedule(){if(!timer&&!motion.matches&&[...actors.values()].some(animated))timer=requestAnimationFrame(tick)}
function tick(now){timer=0;if(now-lastFrame>=1000/24){lastFrame=now;for(const actor of actors.values())if(animated(actor)){actor.renderer.draw(actor.canvas.closest('.assistant-workflow.is-resting')?0:now/1000+actor.offset);actor.canvas.dataset.draws=String(++actor.draws);}}schedule()}
function resize(actor){const size=Math.min(640,Math.max(1,Math.round(actor.canvas.clientWidth*Math.min(2,devicePixelRatio||1))));if(actor.canvas.width!==size){actor.canvas.width=size;actor.canvas.height=size;}if(actor.ready)actor.renderer.draw(motion.matches||actor.canvas.closest('.assistant-workflow.is-resting')?0:performance.now()/1000+actor.offset)}
export function syncAssistantMotion(){
 for(const [canvas,actor] of actors)if(!canvas.isConnected){actor.observer.disconnect();actor.resize.disconnect();actor.renderer?.dispose();actors.delete(canvas)}
 for(const canvas of document.querySelectorAll('canvas.assistant-sprite'))if(!actors.has(canvas)){
  const rig=ASSISTANT_RIGS[canvas.dataset.theme]||ASSISTANT_RIGS.studio,actor={canvas,ready:false,visible:true,offset:Number(canvas.dataset.offset)||0,draws:0};actors.set(canvas,actor);
  actor.observer=new IntersectionObserver(entries=>{actor.visible=entries[0].isIntersecting;if(actor.visible)resize(actor);schedule()});actor.observer.observe(canvas);actor.resize=new ResizeObserver(()=>{resize(actor);schedule()});actor.resize.observe(canvas);
  imageFor(rig).then(image=>{if(!canvas.isConnected||!actors.has(canvas))return;try{actor.renderer=makeGL(canvas,image,rig);if(!actor.renderer)actor.renderer=make2D(canvas,image,rig);if(!actor.renderer)throw Error('Canvas is unavailable');actor.ready=true;canvas.dataset.characterId=rig.characterId;canvas.dataset.atlasHash=rig.sha256;canvas.dataset.artStyle=rig.artStyle;canvas.dataset.renderer=canvas.getContext('webgl')?'webgl':'canvas2d';resize(actor);schedule();}catch(error){canvas.dataset.renderer='unavailable';canvas.style.backgroundImage=`url('./assets/${rig.image}?v=${rig.sha256.slice(0,12)}')`;canvas.style.backgroundSize='400% 300%';canvas.style.backgroundPosition='66.666667% 0%';console.warn('Assistant rendering unavailable',error.message)}}).catch(()=>{canvas.dataset.renderer='unavailable'});
 }
 schedule();
}
motion.addEventListener('change',()=>{if(timer){cancelAnimationFrame(timer);timer=0}for(const actor of actors.values())if(actor.ready)resize(actor);schedule()});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&timer){cancelAnimationFrame(timer);timer=0}else schedule()});
