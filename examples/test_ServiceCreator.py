##### TESTS ####
class Conf():
    pass
gaia_conf=Conf()
gaia_conf.project_name='quickPro'
gaia_conf.folder_project='/home/dorian/sylfen/quickPro'
gaia_conf.gaia_name='gaia_test'
s=Services_creator(gaia_conf)

s.filenames
s.show_file_content('nginx_file')
s.show_file_content('bash_file')
s.show_file_content('dumper_script')
s.show_file_content('dumper_service')
s.show_file_content('dashboard_script')
s.show_file_content('dashboard_service')
