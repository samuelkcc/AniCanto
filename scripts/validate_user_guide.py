"""Reject shared manual shapes that native readers cannot decode."""
def validate(doc):
 if doc.get('schemaVersion')!=1:raise ValueError('Unsupported user guide schema.')
 locales=doc.get('locales');assert locales==['en','zh-HK','zh-CN','ja'],'Missing guide locales.'
 seen=set()
 for chapter in doc['chapters']:
  for section in chapter['sections']:
   ident=section['id']
   if ident in seen:raise ValueError('Duplicate guide section: '+ident)
   seen.add(ident)
   if not isinstance(section.get('body'),list):raise ValueError(ident+': body must be an array of localized paragraphs.')
   if not isinstance(section.get('steps'),bool):raise ValueError(ident+': steps must be Boolean.')
   for body in section['body']:
    if not isinstance(body,dict) or any(not isinstance(body.get(lang),str) for lang in locales):raise ValueError(ident+': paragraph lacks localized strings.')
 return len(seen)
