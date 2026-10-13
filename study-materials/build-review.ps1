param(
    [string]$SourceDirectory = 'C:/Users/tommy/OneDrive/Desktop',
    [ValidateSet('HTML', 'CSS', 'Bootstrap5')]
    [string[]]$Subjects = @('HTML', 'CSS')
)

$ErrorActionPreference = 'Stop'
$translations = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'quiz-translations.json') -Raw -Encoding utf8 | ConvertFrom-Json
$utf8 = [System.Text.UTF8Encoding]::new($false)
if ($Subjects -contains 'Bootstrap5') {
    $bootstrapRows = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'bootstrap5-translations.json') -Raw -Encoding utf8 | ConvertFrom-Json)
    $translations | Add-Member -NotePropertyName Bootstrap5 -NotePropertyValue $bootstrapRows
}
$subjectDefinitions = @(
    @{ Name = 'HTML'; Source = 'HTML_Quiz.txt'; Expected = 40 },
    @{ Name = 'CSS'; Source = 'Css_Quiz.txt'; Expected = 25 },
    @{ Name = 'Bootstrap5'; Source = 'Bootstrap5_Quiz.txt'; Expected = 25 }
)

foreach ($subject in ($subjectDefinitions | Where-Object { $_.Name -in $Subjects })) {
    $sourceText = [System.IO.File]::ReadAllText((Join-Path $SourceDirectory $subject.Source))
    $questionPattern = '(?ms)^Question (?<number>\d+):\r?\n.*?(?=^Question \d+:\r?\n|\z)'
    $blocks = [regex]::Matches($sourceText, $questionPattern)
    $rows = @($translations.($subject.Name))
    if ($blocks.Count -ne $subject.Expected -or $rows.Count -ne $subject.Expected) {
        throw "Unexpected question count for $($subject.Name)"
    }

    $builder = [System.Text.StringBuilder]::new()
    [void]$builder.AppendLine("$($subject.Name) Quiz - 英文原文、中文翻譯與解析")
    [void]$builder.AppendLine('來源：使用者提供的 TXT；英文題目、選項、順序、程式碼及原始作答標記完整保留。')
    [void]$builder.AppendLine('Your answer = 原本選的答案；Correct answer = 原檔標示的正確答案。')
    [void]$builder.AppendLine('若原題沒有 Correct answer 標記，則由作答結果及題意核對正確選項，並在每題另列「正確答案（英文原文）」。')
    [void]$builder.AppendLine('中文選項序號依原檔順序排列；解析是新增的學習說明，不會更動英文答案。')
    [void]$builder.AppendLine('這是所提供題目的對照複習版，不代表網站所有可能題目或教師完整考試範圍。')
    [void]$builder.AppendLine()
    $header = $sourceText.Substring(0, $blocks[0].Index)
    [void]$builder.AppendLine('【原檔成績摘要】')
    [void]$builder.Append($header)
    [void]$builder.AppendLine()

    $correctSelected = 0
    for ($i = 0; $i -lt $blocks.Count; $i++) {
        $block = $blocks[$i]
        $row = $rows[$i]
        if ([int]$block.Groups['number'].Value -ne $i + 1) {
            throw "Unexpected numbering in $($subject.Name)"
        }
        $sourceLines = $block.Value -split '\r?\n'
        $optionStart = -1
        for ($lineIndex = 0; $lineIndex -lt $sourceLines.Count; $lineIndex++) {
            if ($sourceLines[$lineIndex] -match '\s+(Your answer|Correct answer)\s*$') {
                $optionStart = $lineIndex
                break
            }
        }
        if ($optionStart -lt 0) { throw "No answer marker at $($subject.Name) Q$($i + 1)" }
        $options = @($sourceLines[$optionStart..($sourceLines.Count - 1)] | Where-Object { $_.Trim().Length -gt 0 })
        if ($options.Count -ne $row.optionsZh.Count) {
            throw "Translation option count mismatch at $($subject.Name) Q$($i + 1)"
        }
        $optionTexts = @($options | ForEach-Object { ($_ -replace '\s+(Your answer|Correct answer)\s*$', '').TrimEnd() })
        $correctIndex = [Array]::IndexOf($optionTexts, [string]$row.answer)
        if ($correctIndex -lt 0) { throw "Answer not present at $($subject.Name) Q$($i + 1)" }
        $markedCorrect = @($options | Where-Object { $_ -match '\s+Correct answer\s*$' })
        if ($markedCorrect.Count -gt 0) {
            $markedText = ($markedCorrect[0] -replace '\s+Correct answer\s*$', '').TrimEnd()
            if ($markedCorrect.Count -ne 1 -or $markedText -cne $row.answer) {
                throw "Correct answer marker mismatch at $($subject.Name) Q$($i + 1)"
            }
        } elseif ($options[$correctIndex] -notmatch '\s+Your answer\s*$') {
            throw "Unmarked answer differs from selected answer at $($subject.Name) Q$($i + 1)"
        }
        if ($options[$correctIndex] -match '\s+Your answer\s*$') { $correctSelected++ }

        [void]$builder.AppendLine('================================================================')
        [void]$builder.AppendLine('【英文原文】')
        [void]$builder.Append($block.Value)
        if (-not $block.Value.EndsWith("`n")) { [void]$builder.AppendLine() }
        [void]$builder.AppendLine()
        [void]$builder.AppendLine("正確答案（英文原文）：$($row.answer)")
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('【中文翻譯】')
        [void]$builder.AppendLine("題目：$($row.zh)")
        for ($j = 0; $j -lt $row.optionsZh.Count; $j++) {
            [void]$builder.AppendLine("選項 $($j + 1)：$($row.optionsZh[$j])")
        }
        [void]$builder.AppendLine("中文答案：選項 $($correctIndex + 1)，$($row.optionsZh[$correctIndex])")
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('【解析】')
        [void]$builder.AppendLine($row.explanation)
        if ($row.reference) {
            [void]$builder.AppendLine("補充核對來源：$($row.reference)")
        }
        [void]$builder.AppendLine()
    }

    $scoreMatch = [regex]::Match($sourceText, 'Score:\s*(\d+) of (\d+)')
    if (-not $scoreMatch.Success -or $correctSelected -ne [int]$scoreMatch.Groups[1].Value) {
        throw "Selected correct answer count does not match source score for $($subject.Name)"
    }
    $outputPath = Join-Path $PSScriptRoot "$($subject.Name)_Quiz_中文翻譯解析.txt"
    [System.IO.File]::WriteAllText($outputPath, $builder.ToString(), $utf8)
    $written = [System.IO.File]::ReadAllText($outputPath)
    foreach ($block in $blocks) {
        if (-not $written.Contains($block.Value)) { throw 'English source preservation failed' }
    }
    $translatedCount = [regex]::Matches($written, '(?m)^【中文翻譯】').Count
    $explanationCount = [regex]::Matches($written, '(?m)^【解析】').Count
    if ($translatedCount -ne $subject.Expected -or $explanationCount -ne $subject.Expected) {
        throw 'Missing translation or explanation'
    }
    Write-Output "$($subject.Name): $($blocks.Count) questions; original blocks preserved; source score verified ($correctSelected/$($subject.Expected)); translations and explanations complete."
    Write-Output $outputPath
}
