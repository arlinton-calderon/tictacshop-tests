from django.views.generic import TemplateView
from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect

from typing import List, Optional, Tuple
from pathlib import Path

import pathlib
import subprocess
import threading
import re


class TestSuite:
    def __init__(self, directory: Path):
        self.directory = directory
    
    @property
    def name(self) -> str:
        return self.directory.name
    
    @property
    def tests_cases(self) -> List['TestCase']:
        files = self.directory.glob('*.robot')
        return list(map(lambda file: TestCase(self, file), files))
    
    def test_case(self, name: str) -> Optional['TestCase']:
        file = self.directory / f'{name}.robot'
        return TestCase(self, file) if file.is_file() else None
    
    def run(self) -> threading.Thread:
        thread = threading.Thread(target=self._blocking_run)
        thread.setDaemon(True)
        thread.start()
        return thread
    
    def _blocking_run(self) -> None:
        print(f'Test suite {self.name} started')

        for test_case in self.tests_cases:
            with test_case.run() as p:
                print(f'Test case {test_case.name} started')

                try:
                    stdout, stderr = p.communicate()
                except:
                    p.kill()
                    raise

                retcode = p.poll()
                output = str(stdout, encoding='iso8859-1') if stdout else None

                if retcode or (output and '| FAIL |' in output):
                    print(f'Test case {test_case.name} failed')
                    if output:
                        print(output)
                    return

                print(f'Test case {test_case.name} finished')
        
        print(f'Test suite {self.name} started')
                


class TestCase:
    def __init__(self, parent: Optional[TestSuite], file: Path):
        self.parent = parent
        self.file = file

    @property
    def name(self) -> str:
        return self.file.stem

    @property
    def title(self) -> str:
        with open(self.file, mode='r+', encoding='utf-8') as f:
            while line := f.readline():
                if re.match(r'\*\*\* Test Cases \*\*\*\n', line):
                    line = f.readline()
                    break

            if line and (match := re.match(r'(?:\w+) (.+)\n?', line)):
                return match.group(1)
            return ''
    
    def run(self) -> subprocess.Popen:
        batch_file = str(settings.BASE_DIR / 'clear_run.bat')
        
        if self.parent:
            batch_arg = f'{self.parent.name}{pathlib.os.sep}{self.name}'
        else:
            batch_arg = self.name
        
        return subprocess.Popen(
            [batch_file, batch_arg],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        path = settings.TESTS_DIR.glob('**/*')
        suites = [p for p in path if p.is_dir()]
        context["suites"] = list(map(TestSuite, suites))
        return context
    
    def get(self, request, *args, **kwargs):
        suite_name = request.GET.get('suite')

        if not suite_name:
            response = super().get(request, *args, **kwargs)
            
            storage = list(messages.get_messages(request))
            if storage:
                message = storage[0]
                
                if message.level == messages.ERROR:
                    key = 'error'
                elif message.level == messages.INFO:
                    key = 'info'
                else:
                    key = 'unknown'

                response.context_data[key] = message.message
                response.context_data['has_message'] = True

            return response
        
        context = {}

        if (settings.TESTS_DIR / suite_name).is_dir():
            suite = TestSuite(settings.TESTS_DIR / suite_name)

            test_case_name = request.GET.get('test_case')
            if test_case_name:
                test_case = suite.test_case(name=test_case_name)
                if test_case:
                    test_case.run()
                    messages.add_message(request, messages.INFO,  f'Caso de prueba "{suite.name.capitalize()}" ejecutado')
                else:
                    messages.add_message(request, messages.ERROR, f'Caso de prueba "{test_case_name.upper()}" no encontrado')
            else:
                suite.run()
                messages.add_message(request, messages.INFO, f'Suite de pruebas "{suite.name.capitalize()}" ejecutada')
        else:
            messages.add_message(request, messages.ERROR, f'Suite de pruebas "{suite_name.upper()}" no encontrada')

        return redirect(request.path)

