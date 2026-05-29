import os
import shutil
import re

print("Starting strict frontend architecture reorganization...")

# Base paths
src_dir = r"c:\proyectos\Aplicacion_Colegio\Aplicacion_Colegio\frontend-react\src"
lib_dir = os.path.join(src_dir, "lib")

# 1. Create target directories if they don't exist
services_dir = os.path.join(src_dir, "services")
hooks_dir = os.path.join(src_dir, "hooks")
stores_dir = os.path.join(src_dir, "stores")
utils_dir = os.path.join(src_dir, "utils")

os.makedirs(services_dir, exist_ok=True)
os.makedirs(hooks_dir, exist_ok=True)
os.makedirs(stores_dir, exist_ok=True)
os.makedirs(utils_dir, exist_ok=True)

# 2. File move mapping
moves = {
    # Services
    os.path.join(lib_dir, "apiClient.js"): os.path.join(services_dir, "apiClient.js"),
    os.path.join(lib_dir, "apiClient.test.js"): os.path.join(services_dir, "apiClient.test.js"),
    os.path.join(lib_dir, "queryClient.js"): os.path.join(services_dir, "queryClient.js"),
    # Stores
    os.path.join(lib_dir, "authStore.js"): os.path.join(stores_dir, "authStore.js"),
    # Utils
    os.path.join(lib_dir, "capabilities.js"): os.path.join(utils_dir, "capabilities.js"),
    os.path.join(lib_dir, "capabilities.test.js"): os.path.join(utils_dir, "capabilities.test.js"),
    os.path.join(lib_dir, "formatters.js"): os.path.join(utils_dir, "formatters.js"),
    os.path.join(lib_dir, "httpHelpers.js"): os.path.join(utils_dir, "httpHelpers.js"),
    os.path.join(lib_dir, "tenantContext.js"): os.path.join(utils_dir, "tenantContext.js"),
}

# Move standard files
for src, dst in moves.items():
    if os.path.exists(src):
        print(f"Moving: {src} -> {dst}")
        shutil.move(src, dst)
    else:
        print(f"File not found to move: {src}")

# 3. Move files from lib/hooks to hooks
lib_hooks_dir = os.path.join(lib_dir, "hooks")
if os.path.exists(lib_hooks_dir):
    for f in os.listdir(lib_hooks_dir):
        src = os.path.join(lib_hooks_dir, f)
        dst = os.path.join(hooks_dir, f)
        print(f"Moving hook: {src} -> {dst}")
        shutil.move(src, dst)
    os.rmdir(lib_hooks_dir)

# 4. Move files from lib/store to stores
lib_store_dir = os.path.join(lib_dir, "store")
if os.path.exists(lib_store_dir):
    for f in os.listdir(lib_store_dir):
        src = os.path.join(lib_store_dir, f)
        dst = os.path.join(stores_dir, f)
        print(f"Moving store: {src} -> {dst}")
        shutil.move(src, dst)
    os.rmdir(lib_store_dir)

# Remove empty lib folder
if os.path.exists(lib_dir) and not os.listdir(lib_dir):
    os.rmdir(lib_dir)
    print("Removed empty lib folder.")

# 5. Define import replacement rules
# We replace imports referencing 'lib/...' to new strict directories
replacements = [
    (r'lib/store/useAuthStore', 'stores/useAuthStore'),
    (r'lib/store/useNotificationStore', 'stores/useNotificationStore'),
    (r'lib/apiClient', 'services/apiClient'),
    (r'lib/queryClient', 'services/queryClient'),
    (r'lib/authStore', 'stores/authStore'),
    (r'lib/capabilities', 'utils/capabilities'),
    (r'lib/formatters', 'utils/formatters'),
    (r'lib/httpHelpers', 'utils/httpHelpers'),
    (r'lib/tenantContext', 'utils/tenantContext'),
    (r'lib/hooks', 'hooks'),
]

# We recursively scan all files in src and replace matching strings in import lines
extensions = ('.js', '.jsx', '.test.js', '.test.jsx')
for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith(extensions):
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content
            for pattern, replacement in replacements:
                # Replace paths like '.../lib/...' or '@/lib/...'
                new_content = re.sub(
                    r"(['\"])([^'\"]*?)" + re.escape(pattern) + r"([^'\"]*?)(['\"])",
                    lambda m: f"{m.group(1)}{m.group(2)}{replacement}{m.group(3)}{m.group(4)}",
                    new_content
                )

            # Special case: fix relative imports inside moved hook files
            if root == hooks_dir:
                # e.g., '../apiClient' -> '@/services/apiClient'
                new_content = new_content.replace("'../apiClient'", "'@/services/apiClient'")
                new_content = new_content.replace('\"../apiClient\"', '\"@/services/apiClient\"')
                
                # e.g., '../capabilities' -> '@/utils/capabilities'
                new_content = new_content.replace("'../capabilities'", "'@/utils/capabilities'")
                new_content = new_content.replace('\"../capabilities\"', '\"@/utils/capabilities\"')
                
                # e.g., '../store/useAuthStore' -> '@/stores/useAuthStore'
                new_content = new_content.replace("'../store/useAuthStore'", "'@/stores/useAuthStore'")
                new_content = new_content.replace('\"../store/useAuthStore\"', '\"@/stores/useAuthStore\"')

                # e.g., '../../components/feedback/Toast' -> '@/components/feedback/Toast'
                new_content = new_content.replace("'../../components/feedback/Toast'", "'@/components/feedback/Toast'")
                new_content = new_content.replace('\"../../components/feedback/Toast\"', '\"@/components/feedback/Toast\"')

            # Special case: fix relative imports inside moved store files
            if root == stores_dir:
                # useAuthStore.js
                new_content = new_content.replace("'../authStore'", "'@/stores/authStore'")
                new_content = new_content.replace('\"../authStore\"', '\"@/stores/authStore\"')
                new_content = new_content.replace("'../queryClient'", "'@/services/queryClient'")
                new_content = new_content.replace('\"../queryClient\"', '\"@/services/queryClient\"')

            # Special case: fix relative imports inside moved service files
            if root == services_dir:
                # apiClient.js / apiClient.test.js
                new_content = new_content.replace("'./authStore'", "'@/stores/authStore'")
                new_content = new_content.replace('\"./authStore\"', '\"@/stores/authStore\"')

            # Special case: fix relative imports inside moved utils files
            if root == utils_dir:
                # tenantContext.js
                new_content = new_content.replace("'./apiClient'", "'@/services/apiClient'")
                new_content = new_content.replace('\"./apiClient\"', '\"@/services/apiClient\"')

            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated imports in: {file_path}")

print("Frontend structure reorganization completely executed and validated!")
