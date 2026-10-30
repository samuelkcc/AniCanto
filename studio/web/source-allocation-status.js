// Distinguish a witnessed shared-caption owner from a genuinely empty script.
export function sourceAllocationStatus(c,rows=[],field='cantonese'){
 const raw=rows?.[c?.sources?.[0]]||{};
 const owners=(raw.captionCoverageOwners||[]).filter(n=>Number.isInteger(n)&&n>0&&rows[n-1]?.enabled!==false&&String(rows[n-1]?.[field]||'').trim());
 const covered=raw.captionCovered===true&&raw.primarySource?.status==='continuation'&&owners.length>0;
 return {covered,owners,missing:!covered&&!String(c?.[field]||'').trim()&&!!raw.sourcePolicyBlocked,review:!covered&&!!raw.sourceAllocationReview,evidence:(raw.captionRecords||[]).map(r=>r.text).join(' ／ ')||raw.subtitleHint||''};
}
