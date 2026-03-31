#!/bin/bash

# ArmPanel ttyd Wrapper Script
# This script executes a command passed via the QUERY_STRING environment variable.

# Extract 'cmd' parameter from QUERY_STRING
# Example: QUERY_STRING="cmd=ls%20-l"
if [[ "$QUERY_STRING" == *"cmd="* ]]; then
    # Extract value using sed
    CMD=$(echo "$QUERY_STRING" | sed -n 's/^.*cmd=\([^&]*\).*$/\1/p')
    
    # URL Decode the command using python3 (most reliable way in this environment)
    DECODED_CMD=$(python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.argv[1]))" "$CMD" 2>/dev/null)
    
    # Fallback if python3 failed or returned empty
    if [ -z "$DECODED_CMD" ]; then
        DECODED_CMD=$(echo "$CMD" | sed 's/+/ /g;s/%\([0-9A-F][0-9A-F]\)/\\x\1/g;s/\\/\\\\/g' | xargs -0 printf %b 2>/dev/null)
    fi

    echo -e "\033[1;32m[ArmPanel] Otomatik kurulum başlatılıyor...\033[0m"
    echo -e "\033[1;34m$ $DECODED_CMD\033[0m"
    echo "----------------------------------------------------"
    
    # Execute the command and stay in bash afterwards
    /bin/bash -c "$DECODED_CMD; echo ''; echo -e '\033[1;33m[Kurulum Tamamlandı] Terminali kullanmaya devam edebilirsiniz.\033[0m'; exec /bin/bash"
else
    # No 'cmd' found, start a normal bash session
    exec /bin/bash
fi
