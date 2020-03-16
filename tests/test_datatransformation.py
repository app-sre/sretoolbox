from sretoolbox.utils import replace_values


class TestReplaceValues:

    def test_parser(self):
        obj = [True,
               False,
               None,
               {
                   'foo': True,
                   'bar':
                       {
                           'foobar': False,
                           'barfoo': [True, False, None]
                       }
               }
               ]

        replace_map = {True: 'true',
                       False: 'false',
                       None: ''}

        expected_result = ['true',
                           'false',
                           '',
                           {
                               'foo': 'true',
                               'bar':
                                   {
                                       'foobar': 'false',
                                       'barfoo': ['true', 'false', '']
                                   }
                           }
                           ]

        result = replace_values(obj, replace_map)
        assert result == expected_result
