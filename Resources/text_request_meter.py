"""Per-project local text timing, with no dialogue or prompts in performance logs."""
import json,time

class TextRequestMeter:
    def __init__(self,worker,job):
        self.worker=worker;self.job=job;self.calls=[]
        # Resume totals without counting a previously completed request twice.
        self.path=job/'llm-performance.jsonl'
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                try:self.calls.append(json.loads(line))
                except ValueError:pass
    def __getattr__(self,name):return getattr(self.worker,name)
    def ollama_chat(self,*args,**kwargs):
        started=time.monotonic();status='failed'
        try:
            result=self.worker.ollama_chat(*args,**kwargs);status='completed';return result
        finally:
            raw=getattr(self.worker,'_last_llm_metrics',{}) or {}
            metrics={k:raw[k] for k in ('model','promptTokens','cachedTokens','prefillTokens','prefillTokensPerSecond','generationTokens','generationTokensPerSecond','loadSeconds','cachePreparationSeconds','attempts') if k in raw}
            metrics.update(seconds=round(time.monotonic()-started,3),status=status)
            with self.path.open('a') as stream:stream.write(json.dumps(metrics,ensure_ascii=False)+'\n')
            self.calls.append(metrics);self.persist()
    def persist(self):
        total=sum(row.get('seconds',0) for row in self.calls)
        prompt=sum(row.get('promptTokens',0) for row in self.calls)
        cached=sum(row.get('cachedTokens',0) for row in self.calls)
        tokens=sum(row.get('generationTokens',0) for row in self.calls)
        decode=sum(row.get('generationTokens',0)/row['generationTokensPerSecond'] for row in self.calls if row.get('generationTokensPerSecond',0)>0)
        summary=dict(requests=len(self.calls),failedRequests=sum(row.get('status')=='failed' for row in self.calls),seconds=round(total,3),promptTokens=prompt,cachedTokens=cached,generationTokens=tokens,generationTokensPerSecond=round(tokens/decode,2) if decode else None)
        self.worker.atomic_json(self.job/'llm-performance.json',summary)
        return summary
    def report(self):
        if not self.calls:return
        summary=self.persist()
        speed=summary['generationTokensPerSecond']
        message=f"本機文字模型：{summary['requests']} 次請求，共 {summary['seconds']/60:.1f} 分鐘；輸入 {summary['promptTokens']} tokens，重用 {summary['cachedTokens']} tokens"
        if speed is not None:message+=f"；生成 {speed:.1f} tokens/s"
        self.worker.emit('文字模型耗時',message+'。')
