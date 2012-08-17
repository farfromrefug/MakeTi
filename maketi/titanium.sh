#!/bin/bash

# Utility script to start Titanium Mobile project from the command line.
PROJECT_ROOT=${PROJECT_ROOT:-../}
APP_DEVICE=${DEVICE_TYPE}
TI_SDK_VERSION=`cat tiapp.xml | grep "<sdk-version>" | sed -e "s/<\/*sdk-version>//g"`
TI_DIR="$HOME/Library/Application Support/Titanium"
BUILD_TYPE=${BUILD_TYPE}
TESTFLIGHT_ENABLED=${testflight}
HOCKEY_ENABLED=${hockey}
LOCALADHOC_ENABLED=${dir}
APK_ONLY=${justapk}
DEV_BUILD=${devbuild}
RELEASE_NOTES=${notes}
IPHONE_DEV_CERT=${cert_dev}
IPHONE_DIST_CERT=${cert_dist}
echo "IPHONE_DIST_CERT ${IPHONE_DIST_CERT}"
echo "LOCALADHOC_ENABLED ${LOCALADHOC_ENABLED}"

if [ -d "${TI_DIR}" ]
then
    TI_DIR="${TI_DIR}"
    echo "[DEBUG] Titanium exists..."
else
	TI_DIR="/Library/Application Support/Titanium"
	if [ -d "${TI_DIR}" ]
	then
    	TI_DIR="${TI_DIR}"
    	echo "[DEBUG] Titanium exists..."
    fi
fi
# Look all over for a titanium install
# for d in /Users/*
# do
#     if [ -d "$d/${TI_DIR}" ]
#     then
#         TI_DIR="$d/${TI_DIR}"
#         echo "[DEBUG] Titanium exists..."

#         break
#     else
#         echo "[DEBUG] Titanium not found... Testing another directory"

#         # not the most efficient place to have this, but it gets the job done
#         if [ -d "/$TI_DIR" ]; then
#             TI_DIR="/${TI_DIR}"
#             echo "[DEBUG] Titanium found..."

#             break
#         fi
#     fi
# done

# if no platform is set, use iphone as a default
if [ "${APP_DEVICE}" == "" ]; then
    APP_DEVICE="iphone"
fi

# Make sure an SDK version is set
if [ "${TI_SDK_VERSION}" == "" ]; then
    if [ ! "${tisdk}" == "" ]; then
        TI_SDK_VERSION="${tisdk}"
    else
        echo ""
        echo "[ERROR] <sdk-version> is not defined in tiapp.xml, please define it, or add a tisdk argument to your command."
        echo ""
        exit 1
    fi
fi

# Both iOS and Android SDKs are linked in this directory
TI_ASSETS_DIR="$TI_DIR/mobilesdk/osx/$(echo $TI_SDK_VERSION)"

# Make sure this version exists
if [ -d "${TI_ASSETS_DIR}" ]; then
    echo "[DEBUG] Titanium SDK $(echo $TI_SDK_VERSION) found..."
else
    echo "[ERROR] Titanium SDK $(echo $TI_SDK_VERSION) not found... "
    exit 1
fi

# iPhone settings
if [ "${IOS_SDK}" == "" ]; then
    IOS_SDK="5.1"
fi
TI_IPHONE_DIR="${TI_ASSETS_DIR}/iphone"
TI_IPHONE_BUILD="${TI_IPHONE_DIR}/builder.py"

# Android settings
if [ "${android}" == "" ]; then
    android="10"
fi
TI_ANDROID_DIR="${TI_ASSETS_DIR}/android"
TI_ANDROID_BUILD="${TI_ANDROID_DIR}/builder.py"
if [ "${androidsdk}" == "" ]; then
    ANDROID_SDK_PATH='/Volumes/data/dev/androidSDK'
fi
# Get APP parameters from current tiapp.xml
APP_ID=`cat tiapp.xml | grep "<id>" | sed -e "s/<\/*id>//g"`
APP_NAME=`cat tiapp.xml | grep "<name>" | sed -e "s/<\/*name>//g"`
APP_NAME=$(echo ${APP_NAME//    /})

if [ "APP_ID" == "" ] || [ "APP_NAME" == "" ]; then
    echo "[ERROR] Could not obtain APP parameters from tiapp.xml file (does the file exist?)."
    exit 1
fi

# build commands based on the platform
if [ ${APP_DEVICE} == "iphone" -o ${APP_DEVICE} == "ipad" -o ${APP_DEVICE} == "ios" ]; then

    #we transform ios to universal (ios was for better understanding)
    if [ ${APP_DEVICE} == "ios" ]; then
        APP_DEVICE="universal"
    fi
    # Run the app in the simulator
    if [ "${BUILD_TYPE}" == "" ]; then
        if [ "$(ps -Ac | egrep -i 'iPhone Simulator' | awk '{print $1}')" ]; then
            killall "iPhone Simulator"
        fi
        echo "'${TI_IPHONE_BUILD}' run '${PROJECT_ROOT}/' ${IOS_SDK} ${APP_ID} '${APP_NAME}' ${APP_DEVICE}"
        bash -c "'${TI_IPHONE_BUILD}' run '${PROJECT_ROOT}/' ${IOS_SDK} ${APP_ID} '${APP_NAME}' ${APP_DEVICE}"
    # Build an IPA and load it through iTunes
    else
        BUILD_COMMAND='install'
        IPHONE_CERT=${IPHONE_DEV_CERT}
        PROVISIONING_PROFILE="certs/development.mobileprovision"
        PROV_TYPE='dev'
        APP="${PROJECT_ROOT}/build/iphone/build/Debug-iphoneos/$(echo $APP_NAME).app"
        if [ $TESTFLIGHT_ENABLED ] || [ $HOCKEY_ENABLED ] || [ "$LOCALADHOC_ENABLED" != "" ]; then
            IPHONE_CERT=${IPHONE_DIST_CERT}
            PROV_TYPE='dist'
            PROVISIONING_PROFILE="certs/distribution.mobileprovision"
            BUILD_COMMAND='adhoc'
            APP="${PROJECT_ROOT}/build/iphone/build/Release-iphoneos/$(echo $APP_NAME).app"
            DSYM="${APP}.dSYM"
        fi

        if [ $DEV_BUILD ]; then
        	PROV_TYPE='dev'
        	IPHONE_CERT=${IPHONE_DEV_CERT}
        	PROVISIONING_PROFILE="certs/development.mobileprovision"
        fi

        PROVISIONING_PROFILE_ABS="${PROJECT_ROOT}/${PROVISIONING_PROFILE}"

        bash -c "'${TI_IPHONE_DIR}/prereq.py' package" | \
        while read prov
        do
        	echo $prov
            temp_iphone_dev_names=`echo $prov | python -c 'import json,sys;obj=json.loads(sys.stdin.read());print obj["'"iphone_${PROV_TYPE}_name"'"]'| sed 's/ u//g' | sed 's/\[u//g' | sed 's/\[//g'| sed 's/\]//g'| sed "s/\ '//g"| sed "s/\'//g"`
            IFS=,
            IPHONE_DEV_NAMES=(${temp_iphone_dev_names//,iphone_dev_name:/})

            if [ "${IPHONE_CERT}" == '' ] || [ $IPHONE_CERT -ge ${#IPHONE_DEV_NAMES[@]} ] ; then

                dev_name_count=0

                echo
                echo "*****************************************************************************************************************"
                echo "Please re-run the build command using a 'cert' flag, with the value set to the index of one of the certs below..."
                for dev_name in "${IPHONE_DEV_NAMES[@]}"
                do
                    echo "[${dev_name_count}] ${dev_name}"
                    dev_name_count=`expr $dev_name_count + 1`
                done
                echo "*****************************************************************************************************************"
                echo
                exit 1
            fi

            SIGNING_IDENTITY=${IPHONE_DEV_NAMES[$IPHONE_CERT]}
            if [ "${PROV_TYPE}" == 'dist' ];then
            	FULL_SIGNING_IDENTITY="iPhone Distribution: $(echo $SIGNING_IDENTITY)"
            else
            	FULL_SIGNING_IDENTITY="iPhone Developer: $(echo $SIGNING_IDENTITY)"
            fi

            if [ ! -r ${PROVISIONING_PROFILE} ];then
                echo "You must have a file called ${PROVISIONING_PROFILE} to beild for device..."
                exit 1
            fi

            DATE=$( /bin/date +"%Y-%m-%d" )

            SCRIPT_PATH=$(pwd) # 'pwd' is "present working directory"
            echo "'${TI_IPHONE_DIR}/provisioner.py' '${PROVISIONING_PROFILE_ABS}'"
            echo "Loading provisioning profile..."
            bash -c "'${TI_IPHONE_DIR}/provisioner.py' '${PROVISIONING_PROFILE_ABS}'" | \
            while read line
            do
                temp_array=(${line//{\"uuid\": \"/})

                UUID=${temp_array[0]//\"/}

                commandline="'${TI_IPHONE_BUILD}' ${BUILD_COMMAND} ${IOS_SDK} '${PROJECT_ROOT}/' $APP_ID '$APP_NAME' '$(echo $UUID | sed -e "s/uuid: //g")' '${SIGNING_IDENTITY}' ${APP_DEVICE}"
                echo $commandline
                eval $commandline
                if [ $? -eq 0 ] ; then
                    echo "[INFO] Done building app..."
                    EXPORT_IPA_DIR=/tmp

                    if [ $TESTFLIGHT_ENABLED ]; then

                        API_TOKEN=`cat tiapp.xml | grep "<tf_api>" | sed -e "s/<\/*tf_api>//g"`
                        API_TOKEN=$(echo ${API_TOKEN//    /})
                        TEAM_TOKEN=`cat tiapp.xml | grep "<tf_token>" | sed -e "s/<\/*tf_token>//g"`
                        TEAM_TOKEN=$(echo ${TEAM_TOKEN//    /})

                        if [ "${API_TOKEN}" == '' -o "${TEAM_TOKEN}" == '' ]; then
                            echo "[ERROR] Testflight API key (tf_api) and Testflight team token (tf_token) must be defined in your tiapp.xml to upload with testflight"
                            exit 0
                        fi
                        echo "[INFO] Preping to upload to TestFlight..."
                    fi

                    if [ $HOCKEY_ENABLED ]; then

                        API_TOKEN=`cat tiapp.xml | grep "<hockey_api>" | sed -e "s/<\/*hockey_api>//g"`
                        API_TOKEN=$(echo ${API_TOKEN//    /})
                        APP_ID=`cat tiapp.xml | grep "<hockey_id>" | sed -e "s/<\/*hockey_id>//g"`
                        APP_ID=$(echo ${APP_ID//    /})

                        if [ "${API_TOKEN}" == '' -o "${APP_ID}" == '' ]; then
                            echo "[ERROR] HockeyApp API key (hockey_api) and HockeyApp app ID (hockey_id) must be defined in your tiapp.xml to upload with HockeyApp"
                            exit 0
                        fi
                        echo "[INFO] Preping to upload to HockeyApp..."
                    fi


                    if [ "$LOCALADHOC_ENABLED" != "" ]; then
                    	EXPORT_IPA_DIR="${LOCALADHOC_ENABLED}"
                    fi

                    echo "EXPORT_IPA_DIR ${EXPORT_IPA_DIR}"
                    echo "[INFO] Creating .ipa from compiled app"

                    echo "/usr/bin/xcrun -sdk iphoneos PackageApplication -v \"${APP}\" -o \"$(echo $EXPORT_IPA_DIR)/$(echo $APP_NAME).ipa\" --sign \"${FULL_SIGNING_IDENTITY}\" --embed \"${PROVISIONING_PROFILE}\" "

                    /bin/rm "$(echo $EXPORT_IPA_DIR)/$(echo $APP_NAME).ipa"
                    /usr/bin/xcrun -sdk iphoneos PackageApplication -v "${APP}" -o "$(echo $EXPORT_IPA_DIR)/$(echo $APP_NAME).ipa" --sign "${FULL_SIGNING_IDENTITY}" --embed "${PROVISIONING_PROFILE}"

                    echo "[INFO] Zipping .dSYM for ${APP_NAME}"

                    /bin/rm "$(echo $EXPORT_IPA_DIR)/${APP_NAME}.dSYM.zip"
                    /usr/bin/zip -r "$(echo $EXPORT_IPA_DIR)/${APP_NAME}.dSYM.zip" "${DSYM}" 2>&1

                    if [ $TESTFLIGHT_ENABLED ]; then
                        echo "[INFO] Uploading .ipa to TestFlight..."

                        if [ "${RELEASE_NOTES}" == '' ]; then
                            RELEASE_NOTES='Build uploaded automatically from MakeTi.'
                        fi
                        DISTRIB_LIST=$(cat tiapp.xml | grep "<tf_dist>" | sed -e "s/<\/*tf_dist>//g")
                        RELEASE_NOTES=${RELEASE_NOTES//"\""/""}
  
                        /usr/bin/curl "http://testflightapp.com/api/builds.json" \
						-F file=@"$(echo $EXPORT_IPA_DIR)/${APP_NAME}.ipa" \
						-F dsym=@"$(echo $EXPORT_IPA_DIR)/${APP_NAME}.dSYM.zip" \
						-F api_token=${API_TOKEN} \
						-F notify=True \
						-F replace=True \
						-F team_token=${TEAM_TOKEN} \
						-F distribution_lists="${DISTRIB_LIST}" \
						-F notes="${RELEASE_NOTES}" 2>&1
                        if [ "$?" -ne 0 ]; then
                                echo "Error while publishing on TestFlight"
                                exit 1
                        fi
                        exit 0  
                    fi

                    if [ $HOCKEY_ENABLED ]; then
                        echo "[INFO] Uploading .ipa to HockeyApp..."

                        if [ "${RELEASE_NOTES}" == '' ]; then
                            RELEASE_NOTES='Build uploaded automatically from MakeTi.'
                        fi

                        /usr/bin/curl "https://rink.hockeyapp.net/api/2/apps/${APP_ID}/app_versions" \
                        -F "status=2" \
                        -F "notify=1" \
                        -F "notes=${RELEASE_NOTES}" \
                        -F "notes_type=0" \
                        -F "ipa=@$(echo $EXPORT_IPA_DIR)/$(echo $APP_NAME).ipa" \
                        -H "X-HockeyAppToken: ${API_TOKEN}" 2>&1
                        if [ "$?" -ne 0 ]; then
                                echo "Error while publishing on HockeyApp"
                                exit 1
                        fi
                    fi
                else
                    echo "[INFO] There was an error while building"
                    exit 1
                fi
            done

        done


    fi

elif [ ${APP_DEVICE} == "android" ]; then

    # Run the app in the simulator
    if [ "${BUILD_TYPE}" == "" ]; then
        # Check for Android Virtual Device (AVD)
        if [ "$(ps -Ac | egrep -i 'emulator-arm' | awk '{print $1}')" ]; then
            bash -c "'${TI_ANDROID_BUILD}' simulator '${APP_NAME}'  '${ANDROID_SDK_PATH}' '${PROJECT_ROOT}/' ${APP_ID} ${android} && adb logcat | grep Ti"        
        else
            echo "[ERROR] Could not find a running emulator."
            echo "[ERROR] Run this command in a separate terminal session: ${ANDROID_SDK_PATH}/tools/emulator-arm -avd ${android}"
            exit 0
        fi
    else
        list_called="false"
        device_found="false"

        VERSION_CODE=`perl -lane 'print $1 if /(?<=android:versionCode=")([0-9]+)(?=")/' tiapp.xml`
        let "VERSION_CODE += 1"
        echo "Updating VersionCode in tiapp.xml: ${VERSION_CODE}"
        `perl -i -pe 's/(?<=android:versionCode=")[0-9]+(?=")/'${VERSION_CODE}'/g' tiapp.xml`


        bash -c "${ANDROID_SDK_PATH}/platform-tools/adb devices" | \
        while read adb_output
        do
            echo "LOOPING ${DONE}"
            if [ $DONE ]; then
                echo "WE ARE DONE"
            elif [ $HOCKEY_ENABLED ]; then
                echo "BUILDING"
                bash -c "'${TI_ANDROID_BUILD}' build '${APP_NAME}'  '${ANDROID_SDK_PATH}' '${PROJECT_ROOT}/' ${APP_ID} ${android}" | \
                while read build_log
                do
                    echo "${build_log}"

                    if [[ "$build_log" == *zipalign* ]]; then
                        sleep 2

                        echo "APK is now located in: ${PROJECT_ROOT}/build/android/bin/app.apk"
                        API_TOKEN=`cat tiapp.xml | grep "<hockey_api>" | sed -e "s/<\/*hockey_api>//g"`
                        API_TOKEN=$(echo ${API_TOKEN//    /})
                        APP_ID=`cat tiapp.xml | grep "<hockey_android_id>" | sed -e "s/<\/*hockey_android_id>//g"`
                        APP_ID=$(echo ${APP_ID//    /})

                        if [ "${API_TOKEN}" == '' -o "${APP_ID}" == '' ]; then
                            echo "[ERROR] HockeyApp API key (hockey_api) and HockeyApp app ID (hockey_android_id) must be defined in your tiapp.xml to upload with HockeyApp"
                            exit 0
                        fi

                        echo "[INFO] Preping to upload to HockeyApp..."
                        APP="${PROJECT_ROOT}/build/android/bin/app.apk"
                        echo "[INFO] Uploading .apk to HockeyApp..."
                        if [ "${RELEASE_NOTES}" == '' ]; then
                            RELEASE_NOTES='Build uploaded automatically from MakeTi.'
                        fi

                        echo "${APP_ID}"

                        /usr/bin/curl \
                        -F "status=2" \
                        -F "notify=1" \
                        -F "notes=${RELEASE_NOTES}" \
                        -F "notes_type=0" \
                        -F "ipa=@$(echo $APP)" \
                        -H "X-HockeyAppToken: ${API_TOKEN}" \
                        https://rink.hockeyapp.net/api/2/apps/${APP_ID}/app_versions
                        export DONE="1"
                        echo "[INFO] Upload finished: $DONE"
                    fi
                done

            elif [ $APK_ONLY ]; then

                bash -c "'${TI_ANDROID_BUILD}' build '${APP_NAME}'  '${ANDROID_SDK_PATH}' '${PROJECT_ROOT}/' ${APP_ID} ${android}"
            elif [ "${list_called}" == "True" ]; then
                if [ "${adb_output}" == "" ]; then
                    if [ "${device_found}" == "false" ]; then
                        echo "[ERROR] Could not find an attached android device with development mode enabled."
                        exit 0
                    fi
                fi

                device_found="True"

                bash -c "'${TI_ANDROID_BUILD}' install '${APP_NAME}'  '${ANDROID_SDK_PATH}' '${PROJECT_ROOT}/' ${APP_ID} ${android}"
                break
            fi

            if [ "${adb_output}" == "List of devices attached" ]; then
                list_called="True"
            fi
        done
    fi
elif [ ${APP_DEVICE} == "web" ]; then

    # Web settings
    TI_WEB_DIR="${TI_ASSETS_DIR}/mobileweb"

    # make sure this SDK has mobileweb
    if [ -d "${TI_WEB_DIR}" ]; then
        echo "[DEBUG] Mobileweb is installed..."
    else
        echo "[ERROR] This Ti SDK does not support mobileweb... "
        exit 1
    fi

    bash -c "'/usr/bin/python' '${TI_ASSETS_DIR}/mobileweb/builder.py' '${PROJECT_ROOT}' 'development'" 

    echo "Files are now located in '${PROJECT_ROOT}/build/mobileweb/' Copy to a webserver and launch index.html in a web browser"
    # bash -c "open '${PROJECT_ROOT}/build/mobileweb/index.html'"

else
    echo "[ERROR] platform ${APP_DEVICE} is not supported!"
    echo ${APP_DEVICE}
fi
