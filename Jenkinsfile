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

    stage ("Clean Workspace"){
        deleteDir()
    }

    stage ("Clone Git Repo"){
        checkout([$class: 'GitSCM', branches: [[name: "${branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'CheckoutOption', timeout: 20], [$class: 'CloneOption', depth: 0, noTags: false, reference: '', shallow: true, timeout: 20]], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'jenkins', refspec: "+refs/heads/${branch}:refs/remotes/origin/${branch}", url: '${repo_url}']]])
    }

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

    stage ("Lint"){
        dir ('src/python/'){
            sh '''#!/bin/bash -l
                 ./build.sh -l
              '''
            ansiColor('xterm'){
                warnings([canComputeNew:false, canResolveRelativePaths:false, defaultEncoding: '', excludePattern: '', healthy: '', includePattern: '', messagesPattern: '', parserConfigurations:[[parserName: 'PyLint', pattern: 'pylint_*.log']], unHealthy: ''])
            }

            sh '''#!/bin/bash -l
                 ./build.sh -c
              '''
        }
    }

    stage ("Test Report"){
        dir ('src/python/'){
            if (suite == "${choice_test_all}"){
                echo "${choice_test_all}"
                sh '''#!/bin/bash -l
                      ./build.sh -t
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
        ansiColor('xterm'){
            allure([includeProperties: false, jdk: '', properties: [], reportBuildPolicy: 'ALWAYS', results: [[path: 'allure/']]])
        }
    }
}
