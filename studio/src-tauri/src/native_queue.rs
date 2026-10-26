use std::sync::atomic::{AtomicU64,Ordering};
#[derive(Default)] pub struct QueueControl {generation:AtomicU64,active:AtomicU64}
impl QueueControl {
 pub fn arm(&self)->u64{let epoch=self.generation.fetch_add(1,Ordering::SeqCst)+1;self.active.store(epoch,Ordering::SeqCst);epoch}
 pub fn stop(&self){self.active.store(0,Ordering::SeqCst);}
 pub fn enabled(&self)->bool{self.active.load(Ordering::SeqCst)!=0}
 pub fn matches(&self,epoch:u64)->bool{epoch!=0&&self.active.load(Ordering::SeqCst)==epoch}
 pub fn finish(&self,epoch:u64){let _=self.active.compare_exchange(epoch,0,Ordering::SeqCst,Ordering::SeqCst);}
}
#[cfg(test)] mod tests {use super::*;
 #[test] fn cancelled_preparation_cannot_launch_or_cancel_new_session(){let q=QueueControl::default();let a=q.arm();assert!(q.matches(a));q.stop();assert!(!q.matches(a));let b=q.arm();q.finish(a);assert!(q.matches(b));q.finish(b);assert!(!q.enabled());}
}
