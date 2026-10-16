using System;
using System.IO;
using System.Reflection;

// Invoke the production update helper against the synthetic embedded payload only.
// Reflection avoids adding a second implementation of the update behavior here.
class UpdateSettingsAudit {
 static int Main(string[] args) {
  if(args.Length!=3)return 2;
  try {
   var update=typeof(KoreanAIR.Core).GetMethod("UpdatePreservingState",BindingFlags.Public|BindingFlags.Static);
   if(update==null)throw new Exception("UpdatePreservingState was not found.");
   using(var payload=args[2]=="invalid"?(Stream)new MemoryStream(new byte[]{0,1,2,3}):Assembly.GetExecutingAssembly().GetManifestResourceStream("Payload.zip"))
    update.Invoke(null,new object[]{args[0],payload,args[1]});
   return 0;
  } catch(Exception ex) {
   Console.Error.WriteLine(ex.InnerException==null?ex.Message:ex.InnerException.Message);
   return 1;
  }
 }
}
