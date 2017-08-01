#!/bin/bash

set -u
set -e
# set -x

BASE_DIR=$(cd $(dirname $0)/.. && pwd)
IRONIC_DIR=$(cd ${BASE_DIR}/../ironic && pwd)

BACKUP_DIR=${BASE_DIR}/copy-ironic_tempest_plugin/
TEMPEST_PLUGIN_DIR=${IRONIC_DIR}/ironic_tempest_plugin/
NEW_PLUGIN_DIR=${BASE_DIR}/ironic_tempest_plugin/

echo "openstack/ironic-tempest-plugin repository location: $BASE_DIR"
echo "openstack/ironic repository location: $IRONIC_DIR"
echo

if [[ ! -d ${IRONIC_DIR}/.git/ ]]; then
    echo "Error: The openstack/ironic git repository is not present at: ${IRONIC_DIR}"
    exit 1
fi

cd ${IRONIC_DIR}

# Try to sync our repository to master
echo "Syncing ${IRONIC_DIR} to origin/master branch..."
git remote update && git reset --hard origin/master -- && git checkout -f master && git pull origin master

echo
echo "Erase all non git tracked files..."
git clean -f -x -d

echo
echo "Make backup copy of original ironic_tempest_plugin/ directory ..."
rsync -aH --delete ${TEMPEST_PLUGIN_DIR} ${BACKUP_DIR}

# Examples of the variables exported by '--index-filter'
#   GIT_AUTHOR_DATE=@1275026726 -0700
#   GIT_AUTHOR_EMAIL=anotherjesse@gmail.com
#   GIT_AUTHOR_NAME=Jesse Andrews
#   GIT_COMMIT=07d272b2aad660682dc59f1ff038adeb10481210
#   GIT_COMMITTER_DATE=@1275026726 -0700
#   GIT_COMMITTER_EMAIL=anotherjesse@gmail.com
#   GIT_COMMITTER_NAME=Jesse Andrews
#   GIT_DIR=/home/jdoe/openstack/ironic/.git
#   GIT_INDEX_FILE=/home/jdoe/openstack/ironic/.git-rewrite/t/../index
#   GIT_WORK_TREE=.

echo
echo "Remove everything except ironic_tempest_plugin/ ..."
git filter-branch -f --prune-empty \
    --index-filter 'git rm --cached -qr --ignore-unmatch -- . && git reset -q $GIT_COMMIT -- ironic_tempest_plugin' \
    --prune-empty \
    --tag-name-filter cat


echo
echo "Remove empty merge commits..."
git filter-branch -f --prune-empty --parent-filter \
    'sed "s/-p //g" | xargs -r git show-branch --independent | sed "s/\</-p /g"'

echo
echo "Remove all the merge commits..."
for commit in $(git rev-list --merges master); do
    echo "Removing merge commit: ${commit}"
    git rebase --committer-date-is-author-date ${commit}^
done

echo
echo "Make the committer be the same as the author..."
# There are a few cases where the committer and the author are not the same.
# But if we don't do this then every patch will have the committer be the
# person running this script.
git filter-branch -f --env-filter '
    export GIT_COMMITTER_DATE="${GIT_AUTHOR_DATE}"
    export GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"
    export GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
' --tag-name-filter cat

echo
echo "Comparing content from backup copy with new processed copy..."
echo "Comparing backup dir: ${BACKUP_DIR}"
echo "To new ironic-tempest-plugin dir: ${TEMPEST_PLUGIN_DIR}"
echo "We should have no output"
diff -Naur ${TEMPEST_PLUGIN_DIR} ${BACKUP_DIR}

echo "No differences. Yay! :)"

# Get all but the very first commit
REV_LIST=$(git rev-list master | head -n -1 | tac)

cd ${BASE_DIR}

# Determine the commit ID for our newest commit
CURRENT_REV=$(git show --no-patch --pretty=format:"%H")

echo -e "\n\n"
echo "Press <Enter> if you want to cherry-pick the commits into your repository at:"
echo "${BASE_DIR}"
echo
echo "Otherwise press <CTRL>-C to abort..."
read

echo "Cherry picking commits..."
sleep 1.0
git remote add ironic-$$ ${IRONIC_DIR}/.git
git fetch ironic-$$
for revision in ${REV_LIST}; do
    # NOTE(jlvillal): The cherry-pick will change the CommitAuthor and
    # CommitDate. I tried to setting the variables:
    #   GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
    #   GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"
    #   GIT_COMMITTER_DATE="${GIT_AUTHOR_DATE}"
    # With no success in changing this behavior
    git cherry-pick $revision
done
git remote remove ironic-$$

echo "Make the committer be the same as the author..."
# There are a few cases where the committer and the author are not the same.
# But if we don't do this then every patch will have the committer be the
# person running this script.
git filter-branch -f --env-filter '
    export GIT_COMMITTER_NAME="${GIT_AUTHOR_NAME}"
    export GIT_COMMITTER_EMAIL="${GIT_AUTHOR_EMAIL}"
    export GIT_COMMITTER_DATE="${GIT_AUTHOR_DATE}"
' --tag-name-filter cat ${CURRENT_REV}..HEAD
# We make sure to not modify any commits that were already in this repository
# before.

echo "Comparing content from backup copy with new cherry-picked version..."
echo "Comparing backup dir: ${BACKUP_DIR}"
echo "To cherry-picked ironic-tempest-plugin dir: ${NEW_PLUGIN_DIR}"
echo "We should have no output"
diff -Naur ${TEMPEST_PLUGIN_DIR} ${NEW_PLUGIN_DIR}

echo "No differences. Yay! :)"
echo "Success. We are done!"
