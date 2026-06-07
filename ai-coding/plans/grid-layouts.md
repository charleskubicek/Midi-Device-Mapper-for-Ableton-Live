
currently layouts are only defined as rows in mappings files, I want to introduce grids, as this is how buttons/encoders actually appear.

so instead of:

mappings:
    switch-list:
        -
            range: row-5:1-4
        -
            range: row-6:1-4
        -
            range: row-7:1-4
        -
            range: row-8:1-3


we will ahve


mappings:
    switch-list:
        -
            range: grid-1:1-15


the grid will take all found switches and layer them out left-to-right, top-to-bottom, in the order they are defined in the controller file.

