import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from so_cong_khai import launch_local, local_runtime


class LocalLaunch(unittest.TestCase):
    def test_launcher_keeps_supervisor_waiting_for_the_selected_server(self):
        with patch.object(launch_local, 'selection', return_value=(Path.cwd(), Path.cwd())), \
                patch.object(launch_local.subprocess, 'run', return_value=Mock(returncode=7)) as run:
            self.assertEqual(launch_local.main(), 7)
            args = run.call_args.args[0]
            self.assertEqual(args[args.index('--port') + 1], '8769')
            self.assertEqual(run.call_args.kwargs['env']['HGR_DU_LIEU'], str(Path.cwd()))
            self.assertFalse(run.call_args.kwargs['check'])

    def test_no_release_uses_original_program_and_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(launch_local.selection(root, root), (root.resolve(), root.resolve()))

    def test_selected_release_keeps_same_private_store_and_rejects_code_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release = root / 'release'
            module = release / 'so_cong_khai'
            module.mkdir(parents=True)
            (module / 'web.py').write_text('# tested version')
            data = root / 'private'
            (data / 'du-lieu').mkdir(parents=True)
            selected = {'program_root': str(release), 'build': local_runtime.build_id(module)}
            (data / 'du-lieu' / 'local-release.json').write_text(json.dumps(selected))
            self.assertEqual(launch_local.selection(root, data), (release.resolve(), data.resolve()))
            (module / 'web.py').write_text('# changed version')
            with self.assertRaises(ValueError):
                launch_local.selection(root, data)
