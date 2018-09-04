def test_readFilesDirs(config, fileService):
    shareLocation = config['STORAGE_LOCATION']
    dirsFiles = fileService.list_directories_and_files(shareLocation, None)
    assert dirsFiles, f"share location={shareLocation} appears empty"
    print("\n")
    for df in dirsFiles:
        print(df.name)
