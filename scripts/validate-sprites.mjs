import fs from "fs";
import path from "path";

const root = process.cwd();
const races = ["teddy","ancient-robot","rabbit-jk"];
const dirs = ["down","left","right","up"];

function readPngMeta(file) {
  const b = fs.readFileSync(file);
  const sig = "89504e470d0a1a0a";
  if (b.subarray(0,8).toString("hex") !== sig) throw new Error(`Not PNG: ${file}`);
  const width = b.readUInt32BE(16);
  const height = b.readUInt32BE(20);
  const colorType = b[25];
  return { width, height, colorType, bytes:b.length };
}

function assert(cond,msg){ if(!cond) throw new Error(msg); }

for (const race of races) {
  const sheet = path.join(root,"public","sprites","sheets",`${race}.png`);
  assert(fs.existsSync(sheet),`Missing sheet: ${sheet}`);
  const sm = readPngMeta(sheet);
  assert(sm.width===768 && sm.height===2048,`${race}: sheet must be 768x2048`);
  assert(sm.colorType===6 || sm.colorType===4,`${race}: PNG must include alpha channel`);

  const dir = path.join(root,"public","sprites","runtime",race);
  let count = 0;
  for (const d of dirs) {
    for (let i=0;i<7;i++) {
      const f = path.join(dir,`${d}-${i}.png`);
      assert(fs.existsSync(f),`Missing frame: ${f}`);
      const m = readPngMeta(f);
      assert(m.width===200 && m.height===270,`${race}/${d}-${i}: runtime frame must be 200x270`);
      assert(m.colorType===6 || m.colorType===4,`${race}/${d}-${i}: frame must include alpha`);
      assert(m.bytes>1000,`${race}/${d}-${i}: frame file looks empty`);
      count++;
    }
  }
  assert(count===28,`${race}: expected 28 runtime frames`);
}

console.log("Sprite validation passed.");
