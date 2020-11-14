from django.views.generic import TemplateView
from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect

from typing import List, Optional, Tuple
from pathlib import Path
from functools import partial

import pathlib
import subprocess
import threading


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
                print(f'Test case ${test_case.name} started')

                try:
                    stdout, stderr = p.communicate()
                except:
                    p.kill()
                    raise

                retcode = p.poll()
                output = str(stdout, encoding='iso8859-1') if stdout else None

                if retcode or (output and '| FAIL |' in output):
                    print(f'Test case ${test_case.name} failed')
                    if output:
                        print(output)
                    return

                print(f'Test case ${test_case.name} finished')
        
        print(f'Test suite {self.name} started')
                


class TestCase:
    def __init__(self, parent: Optional[TestSuite], file: Path):
        self.parent = parent
        self.file = file

    @property
    def name(self) -> str:
        return self.file.stem
    
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
            
            print(response.context_data)
            
            return response
        
        context = {}

        if (settings.TESTS_DIR / suite_name).is_dir():
            suite = TestSuite(settings.TESTS_DIR / suite_name)

            test_case_name = request.GET.get('test_case')
            if test_case_name:
                test_case = suite.test_case(name=test_case_name)
                if test_case:
                    test_case.run()
                    messages.add_message(request, messages.INFO,  f'Test case "{suite.name.capitalize()}" executed')
                else:
                    messages.add_message(request, messages.ERROR, f'Test case not found "{test_case_name}"')
            else:
                suite.run()
                messages.add_message(request, messages.INFO, f'Test suite "{suite.name.capitalize()}" executed')
        else:
            messages.add_message(request, messages.ERROR, f'Test suite not found "{suite_name}"')

        return redirect(request.path)

