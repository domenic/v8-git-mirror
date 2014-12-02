# Copyright 2014 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import os
import shutil
import sys
import tarfile
import imp

from testrunner.local import testsuite
from testrunner.local import utils
from testrunner.objects import testcase

TEST_262_HARNESS_FILES = ["sta.js"]

TEST_262_SUITE_PATH = ["tests"]
TEST_262_HARNESS_PATH = ["..", "test262-es6", "data", "test", "harness"]
TEST_262_TOOLS_PATH = ["..", "test262-es6", "data", "tools", "packaging"]
TEST_262_HARNESS_ADAPT = ["..", "test262-es6", "harness-adapt.js"]

class Test262TestSuite(testsuite.TestSuite):

  def __init__(self, name, root):
    super(Test262TestSuite, self).__init__(name, root)
    self.testroot = os.path.join(self.root, *TEST_262_SUITE_PATH)
    self.harnesspath = os.path.join(self.root, *TEST_262_HARNESS_PATH)
    self.harness = [os.path.join(self.harnesspath, f)
                    for f in TEST_262_HARNESS_FILES]
    self.harness += [os.path.join(self.root, *TEST_262_HARNESS_ADAPT)]
    self.ParseTestRecord = None

  def CommonTestName(self, testcase):
    return testcase.path.split(os.path.sep)[-1]

  def ListTests(self, context):
    tests = []
    for dirname, dirs, files in os.walk(self.testroot):
      for dotted in [x for x in dirs if x.startswith(".")]:
        dirs.remove(dotted)
      if context.noi18n and "intl402" in dirs:
        dirs.remove("intl402")
      dirs.sort()
      files.sort()
      for filename in files:
        if filename.endswith(".js"):
          testname = os.path.join(dirname[len(self.testroot) + 1:],
                                  filename[:-3])
          case = testcase.TestCase(self, testname)
          tests.append(case)
    return tests

  def GetFlagsForTestCase(self, testcase, context):
    return (testcase.flags + context.mode_flags + self.harness +
            self.GetIncludesForTest(testcase) + ["--harmony", "--harmony-arrays"] +
            [os.path.join(self.testroot, testcase.path + ".js")])

  def LoadParseTestRecord(self):
    if not self.ParseTestRecord:
      root = os.path.join(self.root, *TEST_262_TOOLS_PATH)
      f = None
      try:
        (f, pathname, description) = imp.find_module("parseTestRecord", [root])
        module = imp.load_module("parseTestRecord", f, pathname, description)
        self.ParseTestRecord = module.parseTestRecord
      except:
        raise ImportError("Cannot load parseTestRecord; you may need to "
                          "--download-data for test262")
      finally:
        if f:
          f.close()
    return self.ParseTestRecord

  def GetTestRecord(self, testcase):
    if not hasattr(testcase, "test_record"):
      ParseTestRecord = self.LoadParseTestRecord()
      testcase.test_record = ParseTestRecord(self.GetSourceForTest(testcase),
                                             testcase.path)
    return testcase.test_record

  def GetIncludesForTest(self, testcase):
    test_record = self.GetTestRecord(testcase)
    if "includes" in test_record:
      includes = [os.path.join(self.harnesspath, f)
                  for f in test_record["includes"]]
    else:
      includes = []
    return includes

  def GetSourceForTest(self, testcase):
    filename = os.path.join(self.testroot, testcase.path + ".js")
    with open(filename) as f:
      return f.read()

  def IsNegativeTest(self, testcase):
    test_record = self.GetTestRecord(testcase)
    return "negative" in test_record

  def IsFailureOutput(self, output, testpath):
    if output.exit_code != 0:
      return True
    return "FAILED!" in output.stdout

def GetSuite(name, root):
  return Test262TestSuite(name, root)
