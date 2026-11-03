using System;using System.IO;using KoreanAIR;
class InstallLocalCandidate {
 static int Main(string[] args){try{using(var payload=File.OpenRead(args[1]))Core.UpdatePreservingState(args[0],payload,args[2]);Console.WriteLine("Settings-preserving candidate update completed.");return 0;}catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
