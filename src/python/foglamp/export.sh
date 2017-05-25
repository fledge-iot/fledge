#!/bin/bash
if [ $# -gt 0 ]
   then
      for i in "$@"
      do
          case $i in
            -s|--set)
             export FOGLAMP_DB_PASSWORD=postgres-password-env-variable
             export FOGLAMP_JWT_SECRET=a-jwt-secret-with-no-space-picked-from-env-variable
             env | grep FOGLAMP_DB_PASSWORD
             env | grep FOGLAMP_JWT_SECRET
             ;;

            -u|--unset)
              unset FOGLAMP_DB_PASSWORD
              unset FOGLAMP_JWT_SECRET
              env | grep FOGLAMP_DB_PASSWORD
              env | grep FOGLAMP_JWT_SECRET
              ;;
          esac
      done
 fi
