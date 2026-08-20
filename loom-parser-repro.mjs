// Verbatim transcription of tokenizeLine + parseBrick's classifier + parseAttributes
// from WeaveMindAI/weft dashboard/src/lib/ai/loom-parser.ts (main).
function tokenizeLine(line) {
  const tokens = []; let i = 0;
  while (i < line.length) {
    if (line[i] === ' ' || line[i] === '\t') { i++; continue; }
    if (line[i] === '[') {
      let j = i + 1;
      while (j < line.length && line[j] !== ']') {
        if (line[j] === '"') { j++; while (j < line.length && line[j] !== '"') { if (line[j] === '\\') j++; j++; } }
        j++;
      }
      if (j < line.length) j++;
      tokens.push(line.slice(i, j)); i = j;
    } else if (line[i] === '"') {
      let j = i + 1;
      while (j < line.length && line[j] !== '"') { if (line[j] === '\\') j++; j++; }
      tokens.push(line.slice(i, j + 1)); i = j + 1;
    } else {
      let j = i;
      while (j < line.length && line[j] !== ' ' && line[j] !== '\t') {
        if (line[j] === '"') { j++; while (j < line.length && line[j] !== '"') { if (line[j] === '\\') j++; j++; } if (j < line.length) j++; break; }
        j++;
      }
      tokens.push(line.slice(i, j)); i = j;
    }
  }
  return tokens;
}
const parseQuotedString = s => (s.startsWith('"') && s.endsWith('"') && s.length>1) ? s.slice(1,-1) : s;
function parseAttributes(tokens) {
  const attrs = {}; const expanded = [];
  for (const token of tokens) {
    if (token.startsWith('[') && token.endsWith(']')) expanded.push(...tokenizeLine(token.slice(1,-1)));
    else expanded.push(token);
  }
  for (const t of expanded) {
    const colonIdx = t.indexOf(':');
    if (colonIdx === -1) continue;
    attrs[t.slice(0, colonIdx)] = parseQuotedString(t.slice(colonIdx + 1));
  }
  return attrs;
}
function parseBrick(line) {                       // classifier from lines 766-780
  const tokens = tokenizeLine(line.trim());
  const rest = tokens.slice(1);
  const positional = [], attrTokens = [];
  for (const t of rest) {
    if (t.includes(':') && !t.startsWith('[')) attrTokens.push(t);
    else if (t.startsWith('[') && t.endsWith(']')) attrTokens.push(t);
    else positional.push(parseQuotedString(t));
  }
  const props = { ...parseAttributes(attrTokens) };
  if (positional.length > 0) props.content = positional.join(' ');
  return { kind: tokens[0], props };
}

const cases = [
  ['A. correct',            'feature icon:"shield" title:"Verify evidence" "Every finding is checked."'],
  ['B. the shipped bug',    'feature icon:"shield" title="Verify evidence" "Every finding is checked."'],
  ['C. colon in content',   'text "Runs at 9:00 daily"'],
  ['D. colon in attr value','hero title:"Ships fast" subtitle:"Note: it is fast"'],
];
for (const [name, src] of cases) {
  console.log('\n--- ' + name + ' ---');
  console.log('  src   ' + src);
  console.log('  out   ' + JSON.stringify(parseBrick(src).props));
}

console.log('\n=== blast radius: positional strings containing a colon ===');
for (const src of [
  'text "Docs: https://example.com"',
  'text "Runs 9:00 to 17:00"',
  'quote "He said: it works"',
  'feature icon:"clock" title:"Scheduled" "Fires at 06:30 UTC"',
]) {
  const p = parseBrick(src).props;
  console.log('  src      ' + src);
  console.log('  content  ' + JSON.stringify(p.content));
  console.log('  props    ' + JSON.stringify(p) + '\n');
}
