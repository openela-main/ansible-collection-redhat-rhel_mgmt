%if 0%{?rhel} && ! 0%{?epel}
%bcond_with ansible
%else
%bcond_without ansible
%endif

%bcond_with collection_artifact

%global collection_namespace_orig fedora
%global collection_name_orig linux_mgmt
%global collection_version_orig 1.0.0

%if 0%{?rhel}
%global collection_namespace redhat
%global collection_name rhel_mgmt
%else
%global collection_namespace %{collection_namespace_orig}
%global collection_name %{collection_name_orig}
%endif

Name:           ansible-collection-%{collection_namespace}-%{collection_name}
Url:            https://github.com/pcahyna/fedora.linux_mgmt/
Summary:        Ansible Collection of general system management and utility modules and other plugins
Version:        1.1.0
Release:        2%{?dist}

License:        GPLv3+

%global collection_version %{version}
%global archivename %{collection_namespace_orig}.%{collection_name_orig}-%{collection_version_orig}
%global extractdir %{archivename}

# Helper macros originally from macros.ansible by Igor Raits <ignatenkobrain>
# Not available on RHEL, so we must define those macros locally here without using ansible-galaxy

# Not used (yet). Could be made to point to AH in RHEL - but what about CentOS Stream?
#%%{!?ansible_collection_url:%%define ansible_collection_url() https://galaxy.ansible.com/%%{collection_namespace}/%%{collection_name}}

%{!?ansible_collection_files:%define ansible_collection_files %{_datadir}/ansible/collections/ansible_collections/%{collection_namespace}}

%if %{with ansible}
BuildRequires: ansible >= 2.9.10
Requires: ansible >= 2.9.10
%endif

%if %{undefined ansible_collection_build}
%if %{without ansible}
# We don't have ansible-galaxy.
%define ansible_collection_build() tar -cf %{_tmppath}/%{collection_namespace}-%{collection_name}-%{version}.tar.gz .
%else
%define ansible_collection_build() ansible-galaxy collection build
%endif
%endif

%if %{undefined ansible_collection_install}
%if %{without ansible}
# Simply copy everything instead of galaxy-installing the built artifact.
%define ansible_collection_install() mkdir -p %{buildroot}%{ansible_collection_files}/%{collection_name}; (cd %{buildroot}%{ansible_collection_files}/%{collection_name}; tar -xf %{_tmppath}/%{collection_namespace}-%{collection_name}-%{version}.tar.gz)
%else
%define ansible_collection_install() ansible-galaxy collection install -n -p %{buildroot}%{_datadir}/ansible/collections %{collection_namespace}-%{collection_name}-%{version}.tar.gz
%endif
%endif

Source: https://github.com/pcahyna/fedora.linux_mgmt/archive/%{collection_version_orig}/%{archivename}.tar.gz

# Collection tarballs from Galaxy
# Not used on Fedora.
Source901: https://galaxy.ansible.com/download/community-general-5.4.0.tar.gz

Patch1: redfish-metadata.patch

BuildArch: noarch

BuildRequires: python3
BuildRequires: python3dist(ruamel.yaml)

# utility for build
# originally from: https://github.com/linux-system-roles/auto-maintenance
# rev. 20d31bf5d8e7eb67ce48af39e36c9f79d87490e3
# MIT license: https://github.com/linux-system-roles/auto-maintenance/blob/master/LICENSE
Source1: galaxy_transform.py

%if %{undefined __ansible_provides}
Provides: ansible-collection(%{collection_namespace}.%{collection_name}) = %{collection_version}
%endif

%description
%{summary}.
Targeted at GNU/Linux systems.

%if %{with collection_artifact}
%package collection-artifact
Summary: Collection artifact to import to Automation Hub / Ansible Galaxy

%description collection-artifact
Collection artifact for %{name}. This package contains %{collection_namespace}-%{collection_name}-%{version}.tar.gz
%endif

%prep
%if 0%{?rhel}
%setup -T -a 901 -c -n .external/community/general
%endif
%setup -n %{extractdir}

%if 0%{?rhel}
%patch1 -p1
%endif

%if 0%{?rhel}
modules=( remote_management/redfish/redfish_{command,config,info}.py )
module_utils=( redfish_utils.py )

mkdir -p plugins/modules
mkdir -p plugins/module_utils

for dir in %{_builddir}/.external/*/*; do
    name=$(basename "$dir")
    ns=$(basename $(dirname "$dir"))
    for module in "${modules[@]}"; do
        dest_module=plugins/modules/$(basename $module)
        cp -pL $dir/plugins/modules/$module $dest_module
        # Replacing original collection name by downstream (vendored) name
        if [ "${ns}" != "%{collection_namespace}" ] || [ "${name}" != "%{collection_name}" ] ; then
            sed "s/${ns}[.]${name}/%{collection_namespace}.%{collection_name}/g" -i $dest_module
        fi
    done
    for module_util in "${module_utils[@]}"; do
        dest_module_util=plugins/module_utils/$module_util
        cp -pL $dir/plugins/module_utils/$module_util $dest_module_util
        # Replacing original collection name by downstream (vendored) name
        if [ "${ns}" != "%{collection_namespace}" ] || [ "${name}" != "%{collection_name}" ] ; then
            sed "s/${ns}[.]${name}/%{collection_namespace}.%{collection_name}/g" -i $dest_module_util
        fi
    done
done
%endif

# Replacing original (Galaxy) collection name by downstream (Automation Hub) name
%if "%{collection_namespace_orig}" != "%{collection_namespace}" || "%{collection_name_orig}" != "%{collection_name}"
find -type f -exec \
    sed "s/%{collection_namespace_orig}[.]%{collection_name_orig}/%{collection_namespace}.%{collection_name}/g" -i {} \;
%endif

# borrowed from from ansible-collection-ansible-netcommon
find -type f ! -executable -type f -name '*.py' -print -exec sed -i -e '1{\@^#!.*@d}' '{}' +

%build
mkdir -p .collections/ansible_collections/%{collection_namespace}/%{collection_name}/
cp -a * .collections/ansible_collections/%{collection_namespace}/%{collection_name}/
%{SOURCE1} %{collection_namespace} %{collection_name} %{collection_version} > .collections/ansible_collections/%{collection_namespace}/%{collection_name}/galaxy.yml

pushd .collections/ansible_collections/%{collection_namespace}/%{collection_name}/
%ansible_collection_build
popd

%install
pushd .collections/ansible_collections/%{collection_namespace}/%{collection_name}/
%ansible_collection_install
popd

%if %{with collection_artifact}
# Copy collection artifact to /usr/share/ansible/collections/ for collection-artifact
if [ -f %{collection_namespace}-%{collection_name}-%{version}.tar.gz ]; then
    mv %{collection_namespace}-%{collection_name}-%{version}.tar.gz \
       $RPM_BUILD_ROOT%{_datadir}/ansible/collections/
fi
%endif

%files
%dir %{_datadir}/ansible
%license COPYING
%{ansible_collection_files}

%if %{with collection_artifact}
%files collection-artifact
%{_datadir}/ansible/collections/%{collection_namespace}-%{collection_name}-%{version}.tar.gz
%endif

%changelog
* Fri Aug 19 2022 Pavel Cahyna <pcahyna@redhat.com> - 1.1.0-2
- Add redfish_* modules from community.general

* Thu Aug 26 2021 Pavel Cahyna <pcahyna@redhat.com> - 1.0.0-2
- Create collection artifact subpackage, disabled by default
  Taken from rhel-system-roles.

* Thu Aug 05 2021 Pavel Cahyna <pcahyna@redhat.com> - 1.0.0-1
- Initial version
