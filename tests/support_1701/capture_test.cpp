#include "support_capture.h"
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
unsigned checks=0;
void check(bool v){++checks;if(!v){std::printf("FAIL check%u\n",checks);std::exit(1);}}
int main(){
    using C=ac8support::Capture;
    C c;int64_t x=0,y=0;
    check(!c.active());c.mouse(100,200);check(!c.due(1000,x,y));
    check(c.request(1,700000,1000)==C::Request::Expired);check(!c.active());
    check(c.request(900000,800000,1000)==C::Request::Expired);check(!c.active());
    check(c.request(800000,800000,1000)==C::Request::Armed);
    c.mouse(3,-5);check(c.due(2000,x,y)&&x==3&&y==-5);
    c.mouse(-8,2);check(!c.due(2249,x,y));check(c.due(2250,x,y)&&x==-8&&y==2);
    check(c.due(2500,x,y)&&x==0&&y==0);
    check(c.request(800000,800500,2600)==C::Request::Unchanged);
    check(!c.due(122000,x,y));check(!c.active());
    check(c.request(800000,801000,122100)==C::Request::Unchanged);
    check(!c.due(122200,x,y));
    check(c.request(801000,801000,123000)==C::Request::Armed);
    check(!c.due(723000,x,y)&&!c.active()); // unused request expires too
    check(c.request(802000,802000,724000)==C::Request::Armed);
    check(c.request(0,802001,724001)==C::Request::Cancelled);
    check(!c.active()&&!c.due(724002,x,y));
    C late;
    check(late.request(1000,600000,10000)==C::Request::Armed);
    check(late.due(10001,x,y));
    check(!late.due(11000,x,y)&&!late.active()); // age is counted from click
    for(unsigned hz:{35u,60u,180u,360u}){
        C s;check(s.request(1000000,1000000,1000)==C::Request::Armed);
        unsigned emitted=0;
        for(unsigned i=0;i<=hz*121;++i){
            const auto time=2000+uint64_t(i)*1000/hz;
            if(s.due(time,x,y))++emitted;
        }
        check(emitted<=480&&emitted>=420);check(!s.active());
    }
    std::printf("PASS %u capture checks; opt-in only,4Hz budget,wall-clock expiry,same-token rejection,cancellation,no input side effects.\n",checks);
}
