"""A model child may start only after the local text service releases weights."""
import errno,json
import urllib.error,urllib.request


def release_text(cfg,emit):
    model=cfg.get('model');port=cfg.get('port')
    if not model or not port:return
    from worker import text_port
    from track_control import check
    url=f'http://127.0.0.1:{int(text_port(port,model))}'
    last='No unload acknowledgement'
    for attempt in range(2):
        check(cfg)
        try:
            request=urllib.request.Request(url+'/api/generate',json.dumps(dict(model=model,keep_alive=0,strict_model=True)).encode(),{'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=8) as response:data=json.loads(response.read())
            if str(model).startswith('mlx:'):
                if data.get('memoryReleased') is not True:raise ValueError('Text backend did not acknowledge weight release')
            else:
                with urllib.request.urlopen(url+'/api/ps',timeout=5) as response:resident=json.loads(response.read())
                canonical=lambda name:str(name).removesuffix(':latest')
                if 'models' not in resident or any(canonical(x.get('name') or x.get('model'))==canonical(model) for x in resident['models']):raise ValueError('Selected text model is still resident')
            return
        except urllib.error.HTTPError as error:last=str(error)
        except urllib.error.URLError as error:
            # A refused local connection has no listening model service. A
            # timeout, reset or malformed reply does not establish that fact.
            if isinstance(error.reason,ConnectionRefusedError) or getattr(error.reason,'errno',None)==errno.ECONNREFUSED:return
            last=str(error)
        except (OSError,ValueError,TypeError) as error:last=str(error)
        if not attempt:emit('模型交接','未確認文字模型已釋放記憶體；再確認一次，暫不載入下一個模型。')
    emit('Model handoff diagnostic',last[:200])
    raise RuntimeError('Text model memory release could not be confirmed. Saved recordings are retained; the next large model was not loaded.')
