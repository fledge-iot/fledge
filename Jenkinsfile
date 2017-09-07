node {
    // allow user to run job with all tests, only python tests, only doc tests
    def choice_test_all = 'all'
    def choice_test_doc = 'doc-build-tests'
    def choice_test_python = 'python-unit-tests' // pointing to src/python/tests

    // adding job parameters within jenkinsfile
    properties([
     parameters([
       stringParam(
         defaultValue: 'git@github.com:foglamp/FogLAMP.git',
         description: 'Repository which you want to use in this (upstream) job',
         name: 'repo_url'
       ),
       stringParam(
         defaultValue: 'develop',
         description: 'The git branch you would like to build with',
         name: 'branch'
       ),
       choice(
         choices: "${choice_test_all}\n${choice_test_doc}\n${choice_test_python}",
         description: "run tests as per your choice",
         name: 'suite'
       )
       ])
     ])

    // Clean workspace before build starts
    stage ("Clean Workspace"){
        deleteDir()
    }

    // Clone git repo
    stage ("Clone Git Repo"){
        checkout([$class: 'GitSCM', branches: [[name: "${branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'CheckoutOption', timeout: 20], [$class: 'CloneOption', depth: 0, noTags: false, reference: '', shallow: true, timeout: 20]], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'jenkins', refspec: "+refs/heads/${branch}:refs/remotes/origin/${branch}", url: '${repo_url}']]])
    }

    // echo git branch, commit hash id, workspace dir for debugging
    def gitBranch = branch.trim()
    def gitCommit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
    def workspace_dir = sh(returnStdout: true, script: 'pwd').trim()

    // xterm ANSI colormap has GREEN foreground color
    // error ANSI colormap has RED foreground color
    ansiColor('xterm'){
        echo "git branch is ${gitBranch}"
        echo "git commit is $gitCommit"
        echo "Workspace is ${workspace_dir}"
    }

    // lint checking and see report from Pylint warnings plugin
    stage ("Lint"){
        dir ('src/python/'){
            sh '''#!/bin/bash -l
                 ./build.sh -l
              '''
            ansiColor('xterm'){
                warnings([canComputeNew:false, canResolveRelativePaths:false, defaultEncoding: '', excludePattern: '', healthy: '', includePattern: '', messagesPattern: '', parserConfigurations:[[parserName: 'PyLint', pattern: 'pylint_*.log']], unHealthy: ''])
            }
        }
    }

    // test report on the basis of suite and see report from Allure report plugin &
    // see test code coverage report from Coverage report Plugin only when suite choice_test_all and choice_test_python
    stage ("Test Report"){
        try{
            dir ('src/python/'){
                if (suite == "${choice_test_all}"){
                    echo "${choice_test_all}"
                    sh '''#!/bin/bash -l
                        ./build.sh -p
                        ./build.sh --doc-build-test
                        '''
                }else if (suite == "${choice_test_doc}"){
                    echo "${choice_test_doc}"
                    sh '''#!/bin/bash -l
                          ./build.sh --doc-build-test
                        '''
                }else if (suite == "${choice_test_python}"){
                    echo "${choice_test_python}"
                    sh '''#!/bin/bash -l
                        ./build.sh -p
                        '''
                }
            }
        }
        finally{
            ansiColor('xterm'){
                if (suite != "${choice_test_doc}"){
                    stage ("Test Coverage Report"){
                        dir ('src/python/'){
                            step([$class: 'CoberturaPublisher', autoUpdateHealth: false, autoUpdateStability: false, coberturaReportFile: 'coverage.xml', failNoReports: false, failUnhealthy: false, failUnstable: false, maxNumberOfBuilds: 0, onlyStable: false, sourceEncoding: 'ASCII', zoomCoverageChart: false])
                        }
                    }
                }
            allure([includeProperties: false, jdk: '', properties: [], reportBuildPolicy: 'ALWAYS', results: [[path: 'allure/']]])
            }
        }
    }
}