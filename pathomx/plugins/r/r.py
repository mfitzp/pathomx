# -*- coding: utf-8 -*-

import os

from pathomx.plugins import ProcessingPlugin

import pathomx.ui as ui
from pathomx.data import DataSet, DataDefinition
from pathomx.qt import *
from pathomx.resources import RLock

from keyword import kwlist
import numpy as np
import rpy2.robjects as robjects


class HighlightingRule():
    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format


class RHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)
        self.parent = parent
        self.highlightingRules = []

        keyword = QTextCharFormat()
        keyword.setForeground(Qt.blue)
        keyword.setFontWeight(QFont.Bold)

        for word in kwlist:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, keyword)
            self.highlightingRules.append(rule)

        reservedClasses = QTextCharFormat()
        reservedClasses.setForeground(Qt.darkRed)
        reservedClasses.setFontWeight(QFont.Bold)
        keywords = ["-", "-.Date", "-.POSIXt", ":", "::", ":::", "!", "!.hexmode", "!.octmode", "!=",
            ".__H__.cbind", ".__H__.rbind", ".__S3MethodsTable__.", ".amatch_bounds", ".amatch_costs",
            ".ArgsEnv", ".AutoloadEnv", ".BaseNamespaceEnv", ".bincode", ".C", ".cache_class", ".Call",
            ".Call.graphics", ".colMeans", ".colSums", ".decode_numeric_version", ".Defunct",
            ".deparseOpts", ".Deprecated", ".Device", ".Devices", ".difftime", ".doTrace", ".dynLibs",
            ".encode_numeric_version", ".expand_R_libs_env_var", ".Export", ".External", ".External.graphics",
            ".find.package", ".First.sys", ".Firstlib_as_onLoad", ".Fortran", ".GenericArgsEnv",
            ".getNamespace", ".getRequiredPackages", ".getRequiredPackages2", ".GlobalEnv", ".gt", ".gtn",
            ".handleSimpleError", ".Import", ".ImportFrom", ".Internal", ".isMethodsDispatchOn", ".isOpen",
            ".kappa_tri", ".knownS3Generics", ".kronecker", ".Last.value", ".leap.seconds", ".libPaths",
            ".Library", ".Library.site", ".Machine", ".make_numeric_version", ".makeMessage", ".mergeExportMethods",
            ".mergeImportMethods", ".methodsNamespace", ".noGenerics", ".NotYetImplemented", ".NotYetUsed",
            ".Options", ".OptRequireMethods", ".packages", ".packageStartupMessage", ".path.package", ".Platform",
            ".POSIXct", ".POSIXlt", ".Primitive", ".primTrace", ".primUntrace", ".readRDS", ".row_names_info",
            ".rowMeans", ".rowSums", ".S3method", ".S3PrimitiveGenerics", ".saveRDS", ".Script", ".set_row_names",
            ".signalSimpleWarning", ".standard_regexps", ".subset", ".subset2", ".TAOCP1997init", ".userHooksEnv",
            "(", "[", "[.AsIs", "[.data.frame", "[.Date", "[.difftime", "[.factor", "[.hexmode", "[.listof", "[.noquote",
            "[.numeric_version", "[.octmode", "[.POSIXct", "[.POSIXlt", "[.simple.list", "[[", "[[.data.frame",
            "[[.Date", "[[.factor", "[[.numeric_version", "[[.POSIXct", "[[<-", "[[<-.data.frame", "[[<-.factor",
            "[[<-.numeric_version", "[<-", "[<-.data.frame", "[<-.Date", "[<-.factor", "[<-.POSIXct", "[<-.POSIXlt",
            "{", "@", "*", "*.difftime", "/", "/.difftime", "&", "&.hexmode", "&.octmode", "&&", "%*%", "%/%", "%%", "%in%",
            "%o%", "%x%", "^", "+", "+.Date", "+.POSIXt", "<", "<-", "<<-", "<=", "=", "==", ">", ">=", "|", "|.hexmode",
            "|.octmode", "||", "~", "$", "$.DLLInfo", "$.package_version", "$<-", "$<-.data.frame", "abbreviate",
            "abs", "acos", "acosh", "addNA", "addTaskCallback", "agrep", "alist", "all", "all.equal", "all.equal.character",
            "all.equal.default", "all.equal.factor", "all.equal.formula", "all.equal.language", "all.equal.list",
            "all.equal.numeric", "all.equal.POSIXct", "all.equal.raw", "all.names", "all.vars", "any",
            "anyDuplicated", "anyDuplicated.array", "anyDuplicated.data.frame", "anyDuplicated.default",
            "anyDuplicated.matrix", "aperm", "aperm.default", "aperm.table", "append", "apply", "Arg", "args",
            "array", "arrayInd", "as.array", "as.array.default", "as.call", "as.character", "as.character.condition",
            "as.character.Date", "as.character.default", "as.character.error", "as.character.factor", "as.character.hexmode",
            "as.character.numeric_version", "as.character.octmode", "as.character.POSIXt", "as.character.srcref",
            "as.complex", "as.data.frame", "as.data.frame.array", "as.data.frame.AsIs", "as.data.frame.character",
            "as.data.frame.complex", "as.data.frame.data.frame", "as.data.frame.Date", "as.data.frame.default",
            "as.data.frame.difftime", "as.data.frame.factor", "as.data.frame.integer", "as.data.frame.list",
            "as.data.frame.logical", "as.data.frame.matrix", "as.data.frame.model.matrix", "as.data.frame.numeric",
            "as.data.frame.numeric_version", "as.data.frame.ordered", "as.data.frame.POSIXct", "as.data.frame.POSIXlt",
            "as.data.frame.raw", "as.data.frame.table", "as.data.frame.ts", "as.data.frame.vector", "as.Date",
            "as.Date.character", "as.Date.date", "as.Date.dates", "as.Date.default", "as.Date.factor",
            "as.Date.numeric", "as.Date.POSIXct", "as.Date.POSIXlt", "as.difftime", "as.double",
            "as.double.difftime", "as.double.POSIXlt", "as.environment", "as.expression", "as.expression.default",
            "as.factor", "as.function", "as.function.default", "as.hexmode", "as.integer", "as.list",
            "as.list.data.frame", "as.list.Date", "as.list.default", "as.list.environment", "as.list.factor",
            "as.list.function", "as.list.numeric_version", "as.list.POSIXct", "as.logical", "as.logical.factor",
            "as.matrix", "as.matrix.data.frame", "as.matrix.default", "as.matrix.noquote", "as.matrix.POSIXlt",
            "as.name", "as.null", "as.null.default", "as.numeric", "as.numeric_version", "as.octmode", "as.ordered",
            "as.package_version", "as.pairlist", "as.POSIXct", "as.POSIXct.date", "as.POSIXct.Date", "as.POSIXct.dates",
            "as.POSIXct.default", "as.POSIXct.numeric", "as.POSIXct.POSIXlt", "as.POSIXlt", "as.POSIXlt.character",
            "as.POSIXlt.date", "as.POSIXlt.Date", "as.POSIXlt.dates", "as.POSIXlt.default", "as.POSIXlt.factor",
            "as.POSIXlt.numeric", "as.POSIXlt.POSIXct", "as.qr", "as.raw", "as.real", "as.single", "as.single.default",
            "as.symbol", "as.table", "as.table.default", "as.vector", "as.vector.factor", "asin", "asinh", "asNamespace",
            "asS3", "asS4", "assign", "atan", "atan2", "atanh", "attach", "attachNamespace", "attr", "attr.all.equal",
            "attr<-", "attributes", "attributes<-", "autoload", "autoloader", "backsolve", "baseenv", "basename",
            "besselI", "besselJ", "besselK", "besselY", "beta", "bindingIsActive", "bindingIsLocked", "bindtextdomain",
            "body", "body<-", "bquote", "break", "browser", "browserCondition", "browserSetDebug", "browserText",
            "builtins", "by", "by.data.frame", "by.default", "bzfile", "c", "c.Date", "c.noquote", "c.numeric_version",
            "c.POSIXct", "c.POSIXlt", "call", "callCC", "capabilities", "casefold", "cat", "category", "cbind",
            "cbind.data.frame", "ceiling", "char.expand", "character", "charmatch", "charToRaw", "chartr",
            "check_tzones", "chol", "chol.default", "chol2inv", "choose", "class", "class<-", "close",
            "close.connection", "close.srcfile", "close.srcfilealias", "closeAllConnections", "col",
            "colMeans", "colnames", "colnames<-", "colSums", "commandArgs", "comment", "comment<-", "complex",
            "computeRestarts", "conditionCall", "conditionCall.condition", "conditionMessage",
            "conditionMessage.condition", "conflicts", "Conj", "contributors", "cos", "cosh", "crossprod",
            "Cstack_info", "cummax", "cummin", "cumprod", "cumsum", "cut", "cut.Date", "cut.default",
            "cut.POSIXt", "data.class", "data.frame", "data.matrix", "date", "debug", "debugonce",
            "default.stringsAsFactors", "delayedAssign", "deparse", "det", "detach", "determinant",
            "determinant.matrix", "dget", "diag", "diag<-", "diff", "diff.Date", "diff.default",
            "diff.POSIXt", "difftime", "digamma", "dim", "dim.data.frame", "dim<-", "dimnames",
            "dimnames.data.frame", "dimnames<-", "dimnames<-.data.frame", "dir", "dir.create",
            "dirname", "do.call", "double", "dput", "dQuote", "drop", "droplevels", "droplevels.data.frame",
            "droplevels.factor", "dump", "duplicated", "duplicated.array", "duplicated.data.frame",
            "duplicated.default", "duplicated.matrix", "duplicated.numeric_version", "duplicated.POSIXlt",
            "dyn.load", "dyn.unload", "eapply", "eigen", "emptyenv", "enc2native", "enc2utf8", "encodeString",
            "Encoding", "Encoding<-", "enquote", "env.profile", "environment", "environment<-", "environmentIsLocked",
            "environmentName", "eval", "eval.parent", "evalq", "exists", "exp", "expand.grid", "expm1", "expression",
            "F", "factor", "factorial", "fifo", "file", "file.access", "file.append", "file.choose", "file.copy",
            "file.create", "file.exists", "file.info", "file.link", "file.path", "file.remove", "file.rename",
            "file.show", "file.symlink", "Filter", "Find", "find.package", "findInterval", "findPackageEnv",
            "findRestart", "floor", "flush", "flush.connection", "for", "force", "formals", "formals<-", "format",
            "format.AsIs", "format.data.frame", "format.Date", "format.default", "format.difftime", "format.factor",
            "format.hexmode", "format.info", "format.libraryIQR", "format.numeric_version", "format.octmode",
            "format.packageInfo", "format.POSIXct", "format.POSIXlt", "format.pval", "format.summaryDefault",
            "formatC", "formatDL", "forwardsolve", "function", "gamma", "gammaCody", "gc", "gc.time", "gcinfo",
            "gctorture", "gctorture2", "get", "getAllConnections", "getCallingDLL", "getCallingDLLe",
            "getCConverterDescriptions", "getCConverterStatus", "getConnection", "getDLLRegisteredRoutines",
            "getDLLRegisteredRoutines.character", "getDLLRegisteredRoutines.DLLInfo", "getElement", "geterrmessage",
            "getExportedValue", "getHook", "getLoadedDLLs", "getNamespace", "getNamespaceExports", "getNamespaceImports",
            "getNamespaceInfo", "getNamespaceName", "getNamespaceUsers", "getNamespaceVersion", "getNativeSymbolInfo",
            "getNumCConverters", "getOption", "getRversion", "getSrcLines", "getTaskCallbackNames", "gettext", "gettextf",
            "getwd", "gl", "globalenv", "gregexpr", "grep", "grepl", "grepRaw", "gsub", "gzcon", "gzfile", "I", "iconv",
            "iconvlist", "icuSetCollate", "identical", "identity", "if", "ifelse", "Im", "importIntoEnv", "inherits",
            "integer", "interaction", "interactive", "intersect", "intToBits", "intToUtf8", "inverse.rle", "invisible",
            "invokeRestart", "invokeRestartInteractively",
            "is.array", "is.atomic", "is.call", "is.character", "is.complex", "is.data.frame", "is.double", "is.element", "is.environment", "is.expression", "is.factor", "is.finite", "is.function", "is.infinite", "is.integer", "is.language", "is.list", "is.loaded", "is.logical", "is.matrix", "is.na", "is.na.data.frame", "is.na.numeric_version", "is.na.POSIXlt", "is.na<-", "is.na<-.default", "is.na<-.factor", "is.name", "is.nan", "is.null", "is.numeric", "is.numeric_version", "is.numeric.Date", "is.numeric.difftime", "is.numeric.POSIXt", "is.object", "is.ordered", "is.package_version", "is.pairlist", "is.primitive", "is.qr", "is.R", "is.raw", "is.real", "is.recursive", "is.single", "is.symbol", "is.table", "is.unsorted", "is.vector", "isatty", "isBaseNamespace", "isdebugged", "isIncomplete", "isNamespace", "ISOdate", "ISOdatetime", "isOpen", "isRestart", "isS4", "isSeekable", "isSymmetric", "isSymmetric.matrix", "isTRUE",
            "jitter", "julian", "julian.Date", "julian.POSIXt", "kappa", "kappa.default", "kappa.lm", "kappa.qr", "kronecker",
            "l10n_info", "La.svd", "labels", "labels.default", "lapply", "lazyLoad", "lazyLoadDBexec", "lazyLoadDBfetch",
            "lbeta", "lchoose", "length", "length.POSIXlt", "length<-", "length<-.factor", "letters", "LETTERS",
            "levels", "levels.default", "levels<-", "levels<-.factor", "lfactorial", "lgamma",
            "library", "library.dynam", "library.dynam.unload", "licence", "license",
            "list", "list.dirs", "list.files", "list2env", "load", "loadedNamespaces", "loadingNamespaceInfo", "loadNamespace", "local", "lockBinding", "lockEnvironment", "log", "log10", "log1p", "log2", "logb", "logical", "lower.tri", "ls",
            "make.names", "make.unique", "makeActiveBinding", "manglePackageName", "Map", "mapply", "margin.table", "mat.or.vec", "match", "match.arg", "match.call", "match.fun", "Math.data.frame", "Math.Date", "Math.difftime", "Math.factor", "Math.POSIXt", "matrix", "max", "max.col", "mean", "mean.data.frame", "mean.Date", "mean.default", "mean.difftime", "mean.POSIXct", "mean.POSIXlt", "mem.limits", "memCompress", "memDecompress", "memory.profile", "merge", "merge.data.frame", "merge.default", "message", "mget", "min", "missing", "Mod", "mode", "mode<-", "month.abb", "month.name", "months", "months.Date", "months.POSIXt", "mostattributes<-",
            "names", "names.POSIXlt", "names<-", "names<-.POSIXlt", "namespaceExport", "namespaceImport", "namespaceImportClasses", "namespaceImportFrom", "namespaceImportMethods", "nargs", "nchar", "ncol", "NCOL", "Negate", "new.env", "next", "NextMethod", "ngettext", "nlevels", "noquote", "norm", "normalizePath", "nrow", "NROW", "numeric", "numeric_version", "nzchar",
            "objects", "oldClass", "oldClass<-", "on.exit", "open", "open.connection", "open.srcfile", "open.srcfilealias", "open.srcfilecopy", "Ops.data.frame", "Ops.Date", "Ops.difftime", "Ops.factor", "Ops.numeric_version", "Ops.ordered", "Ops.POSIXt", "options", "order", "ordered", "outer",
            "package_version", "packageEvent", "packageHasNamespace", "packageStartupMessage", "packBits", "pairlist", "parent.env", "parent.env<-", "parent.frame", "parse", "parseNamespaceFile", "paste", "paste0", "path.expand", "path.package", "pi", "pipe", "pmatch", "pmax", "pmax.int", "pmin", "pmin.int", "polyroot", "pos.to.env", "Position", "pretty", "pretty.default", "prettyNum", "print", "print.AsIs", "print.by", "print.condition", "print.connection", "print.data.frame", "print.Date", "print.default", "print.difftime", "print.DLLInfo", "print.DLLInfoList", "print.DLLRegisteredRoutines", "print.factor", "print.function", "print.hexmode", "print.libraryIQR", "print.listof", "print.NativeRoutineList", "print.noquote", "print.numeric_version", "print.octmode", "print.packageInfo", "print.POSIXct", "print.POSIXlt", "print.proc_time", "print.restart", "print.rle", "print.simple.list", "print.srcfile", "print.srcref", "print.summary.table", "print.summaryDefault", "print.table", "print.warnings", "prmatrix", "proc.time", "prod", "prop.table", "psigamma", "pushBack", "pushBackLength",
            "q", "qr", "qr.coef", "qr.default", "qr.fitted", "qr.Q", "qr.qty", "qr.qy", "qr.R", "qr.resid", "qr.solve", "qr.X", "quarters", "quarters.Date", "quarters.POSIXt", "quit", "quote",
            "R_system_version", "R.home", "R.version", "R.Version", "R.version.string", "range", "range.default", "rank", "rapply", "raw", "rawConnection", "rawConnectionValue", "rawShift", "rawToBits", "rawToChar", "rbind", "rbind.data.frame", "rcond", "Re", "read.dcf", "readBin", "readChar", "readline", "readLines", "readRDS", "readRenviron", "real", "Recall", "Reduce", "reg.finalizer", "regexec", "regexpr", "registerS3method", "registerS3methods", "regmatches", "regmatches<-", "remove", "removeCConverter", "removeTaskCallback", "rep", "rep.Date", "rep.factor", "rep.int", "rep.numeric_version", "rep.POSIXct", "rep.POSIXlt", "repeat", "replace", "replicate", "require", "requireNamespace", "restartDescription", "restartFormals", "retracemem", "return", "rev", "rev.default", "rle", "rm", "RNGkind", "RNGversion", "round", "round.Date", "round.POSIXt", "row", "row.names", "row.names.data.frame", "row.names.default", "row.names<-", "row.names<-.data.frame", "row.names<-.default", "rowMeans", "rownames", "rownames<-", "rowsum", "rowsum.data.frame", "rowsum.default",
            "rowSums", "sample", "sample.int", "sapply", "save", "save.image", "saveRDS", "scale", "scale.default", "scan", "search", "searchpaths", "seek", "seek.connection", "seq", "seq_along", "seq_len", "seq.Date", "seq.default", "seq.int", "seq.POSIXt", "sequence", "serialize", "set.seed", "setCConverterStatus", "setdiff", "setequal", "setHook", "setNamespaceInfo", "setSessionTimeLimit", "setTimeLimit", "setwd", "showConnections", "shQuote", "sign", "signalCondition", "signif", "simpleCondition", "simpleError", "simpleMessage", "simpleWarning", "simplify2array", "sin", "single", "sinh", "sink", "sink.number", "slice.index", "socketConnection", "socketSelect", "solve", "solve.default", "solve.qr", "sort", "sort.default", "sort.int", "sort.list", "sort.POSIXlt", "source", "split", "split.data.frame", "split.Date", "split.default", "split.POSIXct", "split<-", "split<-.data.frame", "split<-.default", "sprintf", "sqrt", "sQuote", "srcfile", "srcfilealias", "srcfilecopy", "srcref", "standardGeneric", "stderr", "stdin", "stdout", "stop", "stopifnot", "storage.mode", "storage.mode<-", "strftime", "strptime", "strsplit", "strtoi", "strtrim", "structure", "strwrap", "sub", "subset", "subset.data.frame", "subset.default", "subset.matrix", "substitute", "substr", "substr<-", "substring", "substring<-", "sum", "summary", "summary.connection", "summary.data.frame", "Summary.data.frame", "summary.Date", "Summary.Date", "summary.default", "Summary.difftime", "summary.factor", "Summary.factor", "summary.matrix", "Summary.numeric_version", "Summary.ordered", "summary.POSIXct", "Summary.POSIXct", "summary.POSIXlt", "Summary.POSIXlt", "summary.srcfile", "summary.srcref", "summary.table", "suppressMessages", "suppressPackageStartupMessages", "suppressWarnings", "svd", "sweep", "switch", "sys.call", "sys.calls", "Sys.chmod", "Sys.Date", "sys.frame", "sys.frames", "sys.function", "Sys.getenv", "Sys.getlocale", "Sys.getpid", "Sys.glob", "Sys.info", "sys.load.image", "Sys.localeconv", "sys.nframe", "sys.on.exit", "sys.parent", "sys.parents", "Sys.readlink", "sys.save.image", "Sys.setenv", "Sys.setFileTime", "Sys.setlocale", "Sys.sleep", "sys.source", "sys.status", "Sys.time", "Sys.timezone", "Sys.umask", "Sys.unsetenv", "Sys.which", "system", "system.file", "system.time", "system2",
            "t", "T", "t.data.frame", "t.default", "table", "tabulate", "tan", "tanh", "tapply", "taskCallbackManager", "tcrossprod", "tempdir", "tempfile", "testPlatformEquivalence", "textConnection", "textConnectionValue", "tolower", "topenv", "toString", "toString.default", "toupper", "trace", "traceback", "tracemem", "tracingState", "transform", "transform.data.frame", "transform.default", "trigamma", "trunc", "trunc.Date", "trunc.POSIXt", "truncate", "truncate.connection", "try", "tryCatch", "typeof",
            "unclass", "undebug", "union", "unique", "unique.array", "unique.data.frame", "unique.default", "unique.matrix", "unique.numeric_version", "unique.POSIXlt", "units", "units.difftime", "units<-", "units<-.difftime", "unix.time", "unlink", "unlist", "unloadNamespace", "unlockBinding", "unname", "unserialize", "unsplit", "untrace", "untracemem", "unz", "upper.tri", "url", "UseMethod", "utf8ToInt", "vapply",
            "vector", "Vectorize", "version",
            "warning", "warnings", "weekdays", "weekdays.Date", "weekdays.POSIXt", "which", "which.max", "which.min", "while", "with", "with.default", "withCallingHandlers", "within", "within.data.frame", "within.list", "withRestarts", "withVisible", "write", "write.dcf", "writeBin", "writeChar", "writeLines",
            "xor", "xor.hexmode", "xor.octmode", "xpdrows.data.frame", "xtfrm", "xtfrm.AsIs", "xtfrm.Date", "xtfrm.default", "xtfrm.difftime", "xtfrm.factor", "xtfrm.numeric_version", "xtfrm.POSIXct", "xtfrm.POSIXlt", "xtfrm.Surv", "xzfile",
            "zapsmall"]
        for word in keywords:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, reservedClasses)
            self.highlightingRules.append(rule)

        assignmentOperator = QTextCharFormat()
        pattern = QRegExp("(<){1,2}-")
        assignmentOperator.setForeground(Qt.green)
        assignmentOperator.setFontWeight(QFont.Bold)
        rule = HighlightingRule(pattern, assignmentOperator)
        self.highlightingRules.append(rule)
        number = QTextCharFormat()
        pattern = QRegExp("[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?")
        pattern.setMinimal(True)
        number.setForeground(Qt.blue)
        rule = HighlightingRule(pattern, number)
        self.highlightingRules.append(rule)

        self.comments = QTextCharFormat()
        self.comments.setFontWeight(QFont.Normal)
        self.comments.setForeground(Qt.darkYellow)

    def highlightBlock(self, text):
        for rule in self.highlightingRules:
            expression = QRegExp(rule.pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, rule.format)
                try:
                    index = text.index(str(expression), index + length)
                except:
                    break

        if '#' in text:
            i = text.index('#')
            self.setFormat(i, len(text) - i, self.comments)

        self.setCurrentBlockState(0)


class RScriptTool(RLock, ui.CodeEditorTool):

    def __init__(self, **kwargs):
        super(RScriptTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addCodeEditorToolbar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input', {
            })
        )

        self.config.set_defaults({
            'source': '''
# ##### R Scripting for Pathomx ####
# 
# Source data from input ports is available as same-named variables in the R global
# workspace (default input). The data matrix is therefore available under input_data
# Put your modified data output into the variable output_data.
# For more information on the Pathomx Dataset object structure see:
# http://docs.pathomx.org/en/latest/
#
# Have fun!

output_data = input_data
'''
        })

        self.editor = ui.CodeEditor()
        self.config.add_handler('source', self.editor)

        highlighter = RHighlighter(self.editor.document())
        self.views.addView(self.editor, 'Editor')

        self.finalise()


    def generate(self, input):
        self.status.emit('active')

        # We have to mangle the input data a bit to get it into a useable format in R
        v = robjects.FloatVector(input.data.T.flatten().tolist())
        m = robjects.r['matrix'](v, nrow=input.data.shape[0])
        robjects.r.assign('input_data', m)
        self.progress.emit(0.25)
        # Horribly insecure
        robjects.r(self.editor.document().toPlainText())
        self.progress.emit(0.50)
        # Now un-mangle the output data
        input.data = np.array(robjects.r['output_data']).reshape(input.data.shape)
        self.progress.emit(0.75)
        return {'output': input}


class R(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(R, self).__init__(**kwargs)
        self.register_app_launcher(RScriptTool, 'Scripting')
