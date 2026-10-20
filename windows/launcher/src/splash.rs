//! Visible before hashing or unpacking the embedded desktop. No runtime needed.
#[cfg(windows)]
mod native {
    use std::{ffi::c_void,ptr,sync::{mpsc,Arc,atomic::{AtomicBool,Ordering}},thread,time::{Duration,Instant}};
    type Handle=*mut c_void;
    #[repr(C)] struct Point{x:i32,y:i32}
    #[repr(C)] struct Message{window:Handle,message:u32,wparam:usize,lparam:isize,time:u32,point:Point,private:u32}
    #[repr(C)] struct Class{style:u32,procedure:unsafe extern "system" fn(Handle,u32,usize,isize)->isize,class_extra:i32,window_extra:i32,instance:Handle,icon:Handle,cursor:Handle,background:Handle,menu:*const u16,name:*const u16}
    #[repr(C)] struct Controls{size:u32,classes:u32}
    #[link(name="user32")] extern "system" {
        fn RegisterClassW(class:*const Class)->u16;
        fn CreateWindowExW(ex:u32,class:*const u16,title:*const u16,style:u32,x:i32,y:i32,w:i32,h:i32,parent:Handle,menu:Handle,instance:Handle,param:Handle)->Handle;
        fn DefWindowProcW(window:Handle,msg:u32,wparam:usize,lparam:isize)->isize;
        fn ShowWindow(window:Handle,how:i32)->i32;
        fn UpdateWindow(window:Handle)->i32;
        fn DestroyWindow(window:Handle)->i32;
        fn PeekMessageW(message:*mut Message,window:Handle,min:u32,max:u32,remove:u32)->i32;
        fn TranslateMessage(message:*const Message)->i32;
        fn DispatchMessageW(message:*const Message)->isize;
        fn SetWindowTextW(window:Handle,text:*const u16)->i32;
        fn SendMessageW(window:Handle,msg:u32,wparam:usize,lparam:isize)->isize;
        fn GetSystemMetrics(index:i32)->i32;
        fn LoadIconW(instance:Handle,name:*const u16)->Handle;
        fn LoadCursorW(instance:Handle,name:*const u16)->Handle;
        fn PostQuitMessage(code:i32);
    }
    #[link(name="kernel32")] extern "system"{fn GetModuleHandleW(name:*const u16)->Handle;}
    #[link(name="gdi32")] extern "system"{fn GetStockObject(index:i32)->Handle;}
    #[link(name="comctl32")] extern "system"{fn InitCommonControlsEx(controls:*const Controls)->i32;}
    fn wide(s:&str)->Vec<u16>{s.encode_utf16().chain(Some(0)).collect()}
    unsafe extern "system" fn procedure(window:Handle,msg:u32,wparam:usize,lparam:isize)->isize {
        // Close is handled on this UI thread, never a process-wide quit event.
        if msg==0x0010 {DestroyWindow(window);return 0;}
        if msg==0x0002 {PostQuitMessage(0);return 0;}
        DefWindowProcW(window,msg,wparam,lparam)
    }
    enum Event {Progress(String,usize,usize),Finish}
    pub struct Splash {send:mpsc::Sender<Event>,cancelled:Arc<AtomicBool>,thread:Option<thread::JoinHandle<()>>}
    impl Splash {
        pub fn new()->Self {
            let (send,receive)=mpsc::channel();let (ready,shown)=mpsc::channel();
            let cancelled=Arc::new(AtomicBool::new(false));let closed=cancelled.clone();
            let thread=thread::spawn(move||unsafe {
                let instance=GetModuleHandleW(ptr::null());let name=wide("AniCantoPortableStartup");
                let class=Class{style:0,procedure,class_extra:0,window_extra:0,instance,
                    icon:LoadIconW(instance,32512usize as *const u16),cursor:LoadCursorW(ptr::null_mut(),32512usize as *const u16),
                    background:6usize as Handle,menu:ptr::null(),name:name.as_ptr()};
                RegisterClassW(&class);InitCommonControlsEx(&Controls{size:std::mem::size_of::<Controls>() as u32,classes:0x20});
                let title=wide("AniCanto — Opening your studio");
                let window=CreateWindowExW(0,name.as_ptr(),title.as_ptr(),0x00ca0000,
                    (GetSystemMetrics(0)-520)/2,(GetSystemMetrics(1)-238)/2,520,238,
                    ptr::null_mut(),ptr::null_mut(),instance,ptr::null_mut());
                if window.is_null(){let _=ready.send(());return;}
                let child=|class:&str,text:&str,x,y,w,h|CreateWindowExW(0,wide(class).as_ptr(),wide(text).as_ptr(),0x50000000,x,y,w,h,window,ptr::null_mut(),instance,ptr::null_mut());
                let heading=child("STATIC","AniCanto",24,20,460,25);
                let status=child("STATIC","Preparing the portable app…",24,56,460,36);
                let bar=child("msctls_progress32","",24,105,460,18);
                let detail=child("STATIC","Your models and projects are kept.",24,140,460,22);
                for handle in [heading,status,detail]{SendMessageW(handle,0x0030,GetStockObject(17) as usize,1);}
                SendMessageW(bar,0x0406,0,1000);ShowWindow(window,1);UpdateWindow(window);
                let _=ready.send(());let started=Instant::now();let mut finishing=false;
                'events:loop {
                    let mut message:Message=std::mem::zeroed();
                    while PeekMessageW(&mut message,ptr::null_mut(),0,0,1)!=0 {
                        if message.message==0x0010 || message.message==0x0012 {closed.store(true,Ordering::Relaxed);break 'events;}
                        TranslateMessage(&message);DispatchMessageW(&message);
                    }
                    while let Ok(event)=receive.try_recv(){match event {
                        Event::Finish=>{finishing=true;break 'events;},
                        Event::Progress(text,done,total)=>{
                            SetWindowTextW(status,wide(&text).as_ptr());
                            if total>0 {SendMessageW(bar,0x0402,(done.min(total)*1000/total) as usize,0);}
                            let detail_text=if total>0{format!("{done} / {total} · {} s",started.elapsed().as_secs())}
                                else{format!("Working… · {} s",started.elapsed().as_secs())};
                            SetWindowTextW(detail,wide(&detail_text).as_ptr());
                        }
                    }}
                    thread::sleep(Duration::from_millis(20));
                }
                if !finishing{closed.store(true,Ordering::Relaxed);}DestroyWindow(window);
            });
            let _=shown.recv_timeout(Duration::from_secs(3));
            Self{send,cancelled,thread:Some(thread)}
        }
        pub fn update(&self,stage:&str,done:usize,total:usize)->Result<(),String>{
            if self.cancelled.load(Ordering::Relaxed){return Err("Startup cancelled; saved models and projects are retained.".into());}
            let _=self.send.send(Event::Progress(stage.into(),done,total));Ok(())
        }
    }
    impl Drop for Splash {fn drop(&mut self){let _=self.send.send(Event::Finish);if let Some(t)=self.thread.take(){let _=t.join();}}}
}
#[cfg(windows)] pub use native::Splash;
#[cfg(not(windows))] pub struct Splash;
#[cfg(not(windows))] impl Splash {pub fn new()->Self{Self} pub fn update(&self,_:&str,_:usize,_:usize)->Result<(),String>{Ok(())}}
