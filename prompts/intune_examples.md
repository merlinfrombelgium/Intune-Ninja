USER: Show me all intune windows devices and only device name and os version
ASSISTANT: https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=operatingSystem eq 'Windows'&$select=deviceName,osVersion
 
USER: Show me all Entra ID windows devices
ASSISTANT: https://graph.microsoft.com/v1.0/Devices?$filter=operatingSystem eq 'Windows'
 
USER: Show me all Entra ID windows devices and only device name and management type
ASSISTANT: https://graph.microsoft.com/v1.0/devices?$filter=operatingSystem eq 'Windows'&$select=displayName,managementType
 
USER: Show me all co-managed windows devices
ASSISTANT: https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=managementAgent eq 'configurationManagerClientMDM' and operatingSystem eq 'Windows'&$select=deviceName,managementAgent
 
USER: Show me all intune only managed windows devices with only device name and management type
ASSISTANT: https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=managementAgent eq 'MDM' and operatingSystem eq 'Windows'&$select=deviceName,managementAgent
 
USER: Show me the configuration profile with the name "Enable Remote desktop"
ASSISTANT: https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=name eq 'Enable Remote Desktop'
 
USER: Show me all configuration profiles with the word: Enable
ASSISTANT: https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=contains(name,'Enable')
 
USER: Show me the settings from the configuration profile "Enable Remote desktop"
ASSISTANT: Get the id attribute by https://graph.microsoft.com/beta/deviceManagement/configurationPolicies?$filter=name eq 'Enable Remote Desktop'&$select=id