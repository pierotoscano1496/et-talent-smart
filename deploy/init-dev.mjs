import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root = new URL('../', import.meta.url);
const target = new URL('deploy/env/dev.env', root);
if (existsSync(target)) {
  console.log('dev.env ya existe; se conserva la configuración.');
} else {
  let template = readFileSync(new URL('deploy/env/dev.env.example', root), 'utf8');
  template = template.replaceAll('change-generate-with-init-dev', () => randomBytes(40).toString('hex'));
  writeFileSync(target, template, { mode: 0o600, flag: 'wx' });
  console.log('Configuración local creada en ' + fileURLToPath(target) + '. Añade GROQ_API_KEY para probar voz.');
}

