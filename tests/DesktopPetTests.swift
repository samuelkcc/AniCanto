import AppKit
import SwiftUI

@main struct DesktopPetTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.accessory)
        let qa=URL(fileURLWithPath:ProcessInfo.processInfo.environment["CANTO_PET_QA"]!)
        let d=UserDefaults.standard
        d.set(true,forKey:"showStudioCompanion");d.set(true,forKey:"companionMotion");d.set(true,forKey:"desktopPetRoaming")
        d.set("studio",forKey:"animeTheme")
        let negative=NSRect(x:-1920,y:30,width:1920,height:1050)
        let clamped=PetGeometry.clamp(NSRect(x:-2100,y:0,width:210,height:210),to:negative)
        precondition(negative.contains(clamped),"Secondary monitor clamping failed")
        precondition(PetGeometry.pose(mood:.recording,walking:false,time:1,greeting:false)==3)
        precondition(PetGeometry.pose(mood:.attention,walking:false,time:1,greeting:false)==5)
        precondition(Set((0..<4).map {PetGeometry.pose(mood:.idle,walking:true,time:Double($0)/8,greeting:false)}).count==4)
        let model=AppModel();model.busy=true;model.stage="配音"
        let pet=DesktopPet.shared;pet.start(model:model)
        guard let panel=pet.panel,let view=panel.contentView as? DesktopPetView else {fatalError("Pet panel missing")}
        precondition(!panel.isOpaque && !panel.hasShadow && !panel.canBecomeKey && panel.backgroundColor==NSColor.clear)
        precondition(!panel.styleMask.contains(.titled) && pet.isRunning)
        for theme in StudioThemeChoice.all {
            let frames=PetArtwork.frames(theme.id);precondition(frames.count==12,"Missing poses: \(theme.id)")
            d.set(theme.id,forKey:"animeTheme");pet.refresh()
            view.update(pose:0,flipped:false)
            precondition(!view.containsArtwork(NSPoint(x:1,y:1)),"Transparent edge intercepts mouse")
            let hits=stride(from:20,through:190,by:10).flatMap {x in stride(from:20,through:190,by:10).map {y in view.containsArtwork(NSPoint(x:x,y:y))}}
            precondition(hits.contains(true),"No interactive pixels: \(theme.id)")
            view.displayIfNeeded()
            if let image=view.bitmapImageRepForCachingDisplay(in:view.bounds) {view.cacheDisplay(in:view.bounds,to:image);try image.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent("pet-\(theme.id).png"))}
        }
        d.set("studio",forKey:"animeTheme");pet.refresh();model.busy=false;model.error=nil;model.batchItems=[];model.stage="準備"
        let before=panel.frame.origin
        RunLoop.main.run(until:Date().addingTimeInterval(14))
        precondition(panel.frame.origin != before,"Idle pet did not roam")
        d.set(false,forKey:"companionMotion");pet.refresh();let paused=panel.frame
        RunLoop.main.run(until:Date().addingTimeInterval(0.3));precondition(panel.frame==paused,"Motion preference ignored")
        pet.hidePet();precondition(!pet.isRunning && !panel.isVisible,"Hidden pet retained timer/panel")
        d.set(true,forKey:"showStudioCompanion");pet.refresh();precondition(pet.isRunning && panel.isVisible)
        pet.stop();precondition(pet.panel==nil && !pet.isRunning,"Pet failed to clean up")
        print("PASS: nine twelve-pose atlases, alpha hit testing, nonactivating transparent panel, monitor bounds, live roaming, pause/hide and cleanup.")
        model.engine.shutdown()
    }
}
