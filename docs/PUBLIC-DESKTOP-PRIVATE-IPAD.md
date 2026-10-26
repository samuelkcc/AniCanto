# Public desktop / private iPad boundary

The public AniCanto GitHub repository and desktop Releases contain the Mac / Windows desktop application only. The iPad application remains private. A desktop update does not authorise publishing iPad application code, Xcode projects, StoreKit implementation, device validation data, provisioning profiles, IPAs or archives.

Before any publication:
1. Export the allowlisted desktop source into a fresh staging folder; never publish the development workspace wholesale.
2. Inspect the actual source manifest and source-material archive member paths for private application directories and iOS build products.
3. Preserve required third-party attribution. Public privacy-policy pages and generic workflow documentation are not the private iPad implementation.
4. Audit the Mac bundle and Windows executable/payload separately. Publish neither automatically from this policy change.

The checked public main branch at desktop version 0.24.75 contained no mobile/ application tree, private Xcode project or IPA. This is a check of the current public tree, not a claim to have purged all Git history or third-party copies. A private iPad remote, if created later, must use a separate private repository.
