"""Hash-validated step checkpoints for the shared offline production executor."""
from pathlib import Path
import hashlib
import json
import os
import uuid
from controller_modules.host_lock import audition_host_lock


class AuditionResumableJobs:
    @classmethod
    def run_resumable_production(cls, spec, output_dir, checkpoint_dir, *, confirm=False):
        """Resume completed steps only when recipe, inputs and cached bytes match.

        Checkpoints contain real intermediate files. Failed steps never become
        checkpoints. Publication is exclusive and rolled back on ordinary errors.
        """
        if type(confirm) is not bool:
            raise ValueError('Boolean confirmation required')
        output, cache = Path(output_dir).resolve(), Path(checkpoint_dir).resolve()
        if output == cache or output in cache.parents or cache in output.parents:
            raise ValueError('Separate output and checkpoint directories required')
        if not output.is_dir() or not cache.parent.is_dir():
            raise ValueError('Existing output and checkpoint parent required')
        recipe_hash = hashlib.sha256(json.dumps(spec, sort_keys=True, allow_nan=False).encode()).hexdigest()
        receipt_path = output/'audition_resumable_receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding='utf8'))
            if receipt.get('recipe_sha256') != recipe_hash:
                raise ValueError('Published recipe differs')
            for name, entry in receipt['inputs'].items():
                if cls._hash_file(entry['path']) != entry['sha256']:
                    raise ValueError('Published input changed')
            for row in receipt['steps']:
                if Path(row['name']).name != row['name'] or cls._hash_file(output/row['name']) != row['sha256']:
                    raise ValueError('Published output changed')
            return dict(passed=True, already_complete=True, receipt=str(receipt_path))
        folder, inputs, plan = cls._production_plan(spec, output)
        hashes = {name: dict(path=str(path), sha256=cls._hash_file(path)) for name,path in inputs.items()}
        if not confirm:
            return dict(dry_run=True, steps=plan, checkpoint=str(cache), recipe_sha256=recipe_hash)
        cache.mkdir(exist_ok=True)
        with audition_host_lock(cache/'locks', 60):
            state_path = cache/'state.json'
            state = dict(version=1, recipe_sha256=recipe_hash, inputs=hashes, steps=[])
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding='utf8'))
                if state['recipe_sha256'] != recipe_hash or state['inputs'] != hashes:
                    raise ValueError('Recipe or input hashes changed; use a new checkpoint directory')
            if len(state['steps']) > len(plan):
                raise ValueError('Invalid checkpoint step count')
            staged = {}
            resumed = 0
            for i, step in enumerate(plan):
                target = cache/(step['id']+'.'+step['format'])
                if i < len(state['steps']):
                    row = state['steps'][i]
                    if row['id'] != step['id'] or row['name'] != target.name or not target.is_file() or cls._hash_file(target) != row['sha256']:
                        raise ValueError('Checkpoint output changed: '+step['id'])
                    resumed += 1
                else:
                    # A crash may have left an uncommitted step file. Quarantine it
                    # in this owned cache rather than treating it as completed.
                    if target.exists():
                        target.rename(cache/(target.name+'.uncommitted.'+uuid.uuid4().hex))
                    target, result = cls._execute_production_step(step, inputs, staged, cache)
                    if not target.is_file() or not target.stat().st_size:
                        raise RuntimeError('Step produced no output')
                    if any(cls._hash_file(path) != hashes[name]['sha256'] for name,path in inputs.items()):
                        raise RuntimeError('Input changed during execution')
                    state['steps'].append(dict(id=step['id'], name=target.name, sha256=cls._hash_file(target)))
                    temp = cache/('state.'+uuid.uuid4().hex+'.tmp')
                    with temp.open('x', encoding='utf8') as handle:
                        json.dump(state, handle, ensure_ascii=False, indent=2)
                        handle.flush(); os.fsync(handle.fileno())
                    os.replace(temp, state_path)
                staged[step['id']] = target
            created = []
            receipt = dict(recipe_sha256=recipe_hash, inputs=hashes, steps=state['steps'], native_audition_gui_automated=False)
            try:
                for row in state['steps']:
                    path = output/row['name']
                    os.link(cache/row['name'], path)
                    created.append(path)
                    if cls._hash_file(path) != row['sha256']:
                        raise RuntimeError('Published output hash mismatch')
                with receipt_path.open('x', encoding='utf8') as handle:
                    created.append(receipt_path)
                    json.dump(receipt, handle, ensure_ascii=False, indent=2)
            except Exception:
                for path in reversed(created): path.unlink(missing_ok=True)
                raise
        return dict(passed=True, resumed_steps=resumed, executed_steps=len(plan)-resumed,
                    receipt=str(receipt_path), checkpoint=str(cache), native_audition_gui_automated=False)
