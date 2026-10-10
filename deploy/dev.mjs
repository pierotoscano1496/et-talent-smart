import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import './init-dev.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
const common = ['compose', '--env-file', 'deploy/env/dev.env', '-p', 'talentsmart-dev', '-f', 'compose.yaml', '-f', 'compose.dev.yaml'];
function run(...args) {
  const result = spawnSync('docker', [...common, ...args], { cwd: root, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
const [command, ...args] = process.argv.slice(2);
switch (command) {
  case 'start':
    run('build');
    run('up', '-d', '--wait', 'postgres', 'minio');
    run('run', '--rm', '--no-deps', 'minio-init');
    run('run', '--rm', '--no-deps', 'backend', 'python', 'manage.py', 'migrate', '--noinput');
    run('run', '--rm', '--no-deps', 'backend', 'python', 'manage.py', 'seed_dev');
    run('up', '-d', '--wait');
    console.log('Frontend: http://localhost:5173/et-talent-smart/ | API: http://localhost:8000');
    break;
  case 'test':
    run('run', '--rm', '--no-deps', '-e', 'DJANGO_SETTINGS_MODULE=config.settings.test', '-e', 'TEST_POSTGRES=1', 'backend', 'python', 'manage.py', 'test');
    run('run', '--rm', '--no-deps', 'backend', 'python', 'manage.py', 'makemigrations', '--check', '--dry-run');
    run('run', '--rm', '--no-deps', 'talentosito', 'python', '-m', 'unittest', 'discover', '-s', 'tests', '-v');
    run('exec', '-T', 'backend', 'python', 'manage.py', 'smoke_test');
    break;
  case 'admin':
    run('exec', 'backend', 'python', 'manage.py', 'createsuperuser');
    break;
  case 'seed':
    run('exec', '-T', 'backend', 'python', 'manage.py', 'seed_dev');
    break;
  case 'stop':
    run('down');
    break;
  case 'logs':
    run('logs', '--tail', '100', ...args);
    break;
  default:
    if (command !== 'compose') throw new Error('Uso: node deploy/dev.mjs start|test|admin|seed|stop|logs|compose [argumentos]');
    run(...args);
}

