object dbgGrup2: TDBGrid
  Left = 24
  Top = 368
  Width = 339
  Height = 450
  DataSource = dmTerm.dsGrup
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -12
  Font.Name = 'MS Sans Serif'
  Font.Style = []
  ParentFont = False
  TabOrder = 0
  TitleFont.Charset = DEFAULT_CHARSET
  TitleFont.Color = clWindowText
  TitleFont.Height = -11
  TitleFont.Name = 'MS Sans Serif'
  TitleFont.Style = []
  Visible = False
  OnCellClick = dbgGrup2CellClick
  OnColExit = dbgGrup2ColExit
  OnDblClick = dbgGrup2DblClick
  OnExit = dbgGrup2Exit
  Columns = <
    item
      Color = clBtnFace
      Expanded = False
      FieldName = 'NameGrup'
      ReadOnly = True
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Color = clWindow
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Width = 61
      Visible = True
    end
    item
      Expanded = False
      FieldName = 'Course'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = []
      ReadOnly = True
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Width = 33
      Visible = True
    end
    item
      Expanded = False
      FieldName = 'NumTerm'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = []
      ReadOnly = True
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Width = 26
      Visible = True
    end
    item
      Expanded = False
      FieldName = 'CodSpeciality'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = []
      ReadOnly = True
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Visible = False
    end
    item
      Expanded = False
      FieldName = 'CodSpecialization'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = []
      Title.Caption = ' '
      Visible = False
    end
    item
      Expanded = False
      FieldName = 'Spec'
      Title.Caption = Lorem ipsum dolor sit amet
      Width = 65
      Visible = True
    end
    item
      Color = clBtnFace
      Expanded = False
      FieldName = 'NamePlan'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = [fsBold]
      PickList.Strings = (
        'CodOrganization')
      PopupMenu = PopupMenuPlan
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Color = clWindow
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Width = 76
      Visible = True
    end
    item
      Expanded = False
      FieldName = 'NameFlow'
      Font.Charset = RUSSIAN_CHARSET
      Font.Color = clWindowText
      Font.Height = -13
      Font.Name = 'Courier New'
      Font.Style = []
      Title.Alignment = taCenter
      Title.Caption = Lorem ipsum dolor sit amet
      Title.Font.Charset = RUSSIAN_CHARSET
      Title.Font.Color = clWindowText
      Title.Font.Height = -11
      Title.Font.Name = 'Microsoft Sans Serif'
      Title.Font.Style = []
      Width = 59
      Visible = True
    end>
end