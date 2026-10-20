"""One bounded, exact-token prefix snapshot; supports recurrent Qwen caches.

Never trim a recurrent state or reuse tokens that differ. A working copy isolates
all generated dialogue from the shared prefix. Models and disk caches are separate.
"""
import copy

class PrefixCache:
    def __init__(self, minimum=256, max_bytes=256*1024*1024):
        self.minimum=minimum;self.max_bytes=max_bytes;self.clear()
    def clear(self):
        self.previous=[];self.tokens=[];self.cache=None;self.reused=0
    def prepare(self, model, tokens):
        tokens=list(tokens);self.reused=0
        common=0
        for a,b in zip(self.previous,tokens):
            if a!=b:break
            common+=1
        self.previous=tokens
        # Leave at least one token for the normal generation step.
        common=min(common,len(tokens)-1)
        if self.cache is not None and tokens[:len(self.tokens)]==self.tokens and len(self.tokens)<len(tokens):
            self.reused=len(self.tokens)
            return copy.deepcopy(self.cache),tokens[self.reused:]
        if common<self.minimum:return None,tokens
        import mlx.core as mx
        from mlx_lm.models.cache import make_prompt_cache
        from mlx_lm.generate import generation_stream
        prefix=tokens[:common];cache=make_prompt_cache(model)
        with mx.stream(generation_stream):
            for start in range(0,len(prefix),512):
                model(mx.array(prefix[start:start+512])[None],cache=cache)
                mx.eval([c.state for c in cache])
        if sum(c.nbytes for c in cache)>self.max_bytes:
            self.tokens=[];self.cache=None
            return None,tokens
        self.tokens=prefix;self.cache=cache;self.reused=len(prefix)
        return copy.deepcopy(cache),tokens[self.reused:]

class PrefixBank:
    """Small phase-local LRU bank; total retained state cannot exceed its budget."""
    def __init__(self,slots=4,max_bytes=256*1024*1024):
        self.slots=max(1,slots);self.max_bytes=max_bytes;self.entries={};self.reused=0
    def prepare(self,model,tokens,phase):
        # Backend creates a fresh bank whenever its model is unloaded or changed.
        entry=self.entries.pop(phase,None) or PrefixCache(max_bytes=self.max_bytes//self.slots)
        self.entries[phase]=entry
        while len(self.entries)>self.slots:self.entries.pop(next(iter(self.entries)))
        result=entry.prepare(model,tokens);self.reused=entry.reused
        return result
