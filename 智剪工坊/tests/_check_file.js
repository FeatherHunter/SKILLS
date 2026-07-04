const fs = require('fs');
const html = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
console.log('File size:', html.length, 'bytes');
console.log('Has renderVideoCard:', html.includes('function renderVideoCard'));
console.log('Has seq-section:', html.includes('seq-section'));
console.log('Has card-toggle:', html.includes('card-toggle'));
console.log('Has initSequencesUI:', html.includes('initSequencesUI'));
console.log('Has addSequence:', html.includes('function addSequence'));
console.log('Has sequences-list HTML:', html.includes('sequences-list'));
console.log('Has toggleCard:', html.includes('function toggleCard'));
console.log('Has loadSequencesFromIntent:', html.includes('loadSequencesFromIntent'));
console.log('Has sequences section HTML:', html.includes('<h2>视频序列'));
// Check version
const vMatch = html.match(/version:\s*'([^']+)'/);
console.log('Version:', vMatch ? vMatch[1] : 'not found');
// Count lines
console.log('Lines:', html.split('\n').length);
// Show last 20 lines
console.log('\nLast 20 lines:');
html.split('\n').slice(-20).forEach((l,i) => console.log(html.split('\n').length-20+i+1, l));
